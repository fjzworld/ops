<template>
  <div class="log-viewer-container">
    <div class="log-header">
      <span class="log-title">实时日志</span>
      <div class="log-actions">
        <el-input
          v-model="filterText"
          placeholder="过滤日志..."
          size="small"
          clearable
          style="width: 200px; margin-right: 12px;"
        />
        <el-button size="small" @click="clearTerminal">
          <el-icon><Delete /></el-icon> 清空
        </el-button>
      </div>
    </div>
    <div ref="terminalContainer" class="terminal-body"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'
import { Delete } from '@element-plus/icons-vue'

const props = defineProps<{
  url: string
}>()

const terminalContainer = ref<HTMLElement | null>(null)
const filterText = ref('')
let term: Terminal | null = null
let fitAddon: FitAddon | null = null
let ws: WebSocket | null = null
let resizeObserver: ResizeObserver | null = null

// Use a simple array for buffer to avoid reactivity overhead
let logBuffer: string[] = []

const initTerminal = () => {
  if (!terminalContainer.value) return

  term = new Terminal({
    cursorBlink: true,
    convertEol: true,
    theme: {
      background: '#1e1e1e',
      foreground: '#d4d4d4',
    },
    fontFamily: 'Menlo, Monaco, "Courier New", monospace',
    fontSize: 14,
    scrollback: 10000
  })

  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)

  term.open(terminalContainer.value)
  
  // Fit on resize
  resizeObserver = new ResizeObserver(() => {
    fitAddon?.fit()
  })
  resizeObserver.observe(terminalContainer.value)
  
  // Initial fit delay
  setTimeout(() => fitAddon?.fit(), 100)
}

const connectWebSocket = () => {
  if (ws) ws.close()
  if (!props.url) return

  ws = new WebSocket(props.url)

  ws.onopen = () => {
    term?.writeln('\x1b[32m>>> Connected to log stream...\x1b[0m')
    fitAddon?.fit()
  }

  ws.onmessage = (event) => {
    const chunk = event.data
    const lines = chunk.split('\n')
    
    // Maintain buffer (limit to 10k lines)
    if (logBuffer.length + lines.length > 10000) {
        logBuffer.splice(0, (logBuffer.length + lines.length) - 10000)
    }
    logBuffer.push(...lines)

    // Write to terminal
    if (!filterText.value) {
        term?.write(chunk)
    } else {
        // Only write matching lines
        for (const line of lines) {
            if (line.toLowerCase().includes(filterText.value.toLowerCase())) {
                term?.writeln(line)
            }
        }
    }
  }

  ws.onerror = (error) => {
    term?.writeln('\r\n\x1b[31m>>> WebSocket Error\x1b[0m')
    console.error('WebSocket Error:', error)
  }

  ws.onclose = () => {
    term?.writeln('\r\n\x1b[33m>>> Connection closed\x1b[0m')
  }
}

const refreshTerminal = () => {
    if (!term) return
    term.clear()
    
    if (!filterText.value) {
        // Write all buffer
        for (const line of logBuffer) {
            term.writeln(line)
        }
    } else {
        // Filter buffer
        const lowerFilter = filterText.value.toLowerCase()
        for (const line of logBuffer) {
            if (line.toLowerCase().includes(lowerFilter)) {
                term.writeln(line)
            }
        }
    }
}

const clearTerminal = () => {
    term?.clear()
    logBuffer = []
}

watch(filterText, () => {
    refreshTerminal()
})

watch(() => props.url, () => {
    connectWebSocket()
})

onMounted(() => {
  initTerminal()
  connectWebSocket()
})

onUnmounted(() => {
  if (resizeObserver) resizeObserver.disconnect()
  if (ws) ws.close()
  if (term) term.dispose()
})
</script>

<style scoped>
.log-viewer-container {
  display: flex;
  flex-direction: column;
  height: 600px;
  background-color: #1e1e1e;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #333;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background-color: #252526;
  border-bottom: 1px solid #333;
}

.log-title {
  color: #ccc;
  font-weight: 600;
}

.log-actions {
  display: flex;
  align-items: center;
}

.terminal-body {
  flex: 1;
  width: 100%;
  overflow: hidden; /* xterm handles scroll */
  padding: 4px;
}
</style>
