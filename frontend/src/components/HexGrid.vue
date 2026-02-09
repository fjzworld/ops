<template>
  <div class="hex-grid-container">
    <div class="hex-grid">
      <div 
        v-for="node in nodes" 
        :key="node.id" 
        class="hex-wrapper"
        @click="$router.push(`/resources/${node.id}`)"
      >
        <div class="hex" :class="node.status">
          <div class="hex-content">
            <span class="node-name">{{ node.name }}</span>
            <span class="node-metric">{{ node.cpu }}%</span>
          </div>
          <div class="hex-glow"></div>
        </div>
      </div>
      <!-- Placeholders to keep grid shape if few nodes -->
      <div v-if="nodes.length < 5" class="hex-wrapper placeholder" v-for="i in (5 - nodes.length)" :key="i">
        <div class="hex empty"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  nodes: Array<{
    id: string | number
    name: string
    ip: string
    cpu: number
    status: 'normal' | 'warning' | 'critical'
  }>
}>()
</script>

<style scoped>
.hex-grid-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
  overflow: hidden;
}

.hex-grid {
  display: flex;
  flex-wrap: wrap;
  width: 90%;
  max-width: 1200px;
  gap: 10px; 
  justify-content: center;
}

.hex-wrapper {
  position: relative;
  width: 100px;
  height: 110px;
  margin: 0 5px;
  /* Hexagon staggering logic implies margin offsets, 
     but for a simple responsive grid, flex-wrap is easier. 
     True honeycomb needs specific row shifting. 
     Let's use a simplified "tech grid" look with hexagons. */
}

.hex {
  width: 100%;
  height: 100%;
  background: rgba(30, 41, 59, 0.6);
  clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  border: 1px solid rgba(255, 255, 255, 0.05); /* Border doesn't work well with clip-path, using inset box-shadow instead? No. */
}

.hex::before {
  content: '';
  position: absolute;
  inset: 2px;
  background: rgba(15, 23, 42, 0.8);
  clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
  z-index: 1;
}

.hex-content {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.node-name {
  font-size: 10px;
  color: #94A3B8;
  max-width: 80px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-metric {
  font-family: 'Fira Code', monospace;
  font-size: 16px;
  font-weight: bold;
  color: #F8FAFC;
}

/* Status Colors & Glows */
.hex.normal .node-metric { color: #22C55E; }
.hex.normal::before { box-shadow: inset 0 0 15px rgba(34, 197, 94, 0.2); }
.hex.normal:hover { transform: scale(1.1); z-index: 10; }

.hex.warning .node-metric { color: #EAB308; }
.hex.warning::before { box-shadow: inset 0 0 15px rgba(234, 179, 8, 0.3); }
.hex.warning { animation: pulse-yellow 2s infinite; }

.hex.critical .node-metric { color: #EF4444; }
.hex.critical::before { box-shadow: inset 0 0 20px rgba(239, 68, 68, 0.4); background: rgba(239, 68, 68, 0.1); }
.hex.critical { animation: pulse-red 1s infinite; }

.hex.empty {
  opacity: 0.2;
  pointer-events: none;
}

@keyframes pulse-red {
  0% { transform: scale(1); filter: drop-shadow(0 0 0 rgba(239, 68, 68, 0)); }
  50% { transform: scale(1.05); filter: drop-shadow(0 0 10px rgba(239, 68, 68, 0.5)); }
  100% { transform: scale(1); filter: drop-shadow(0 0 0 rgba(239, 68, 68, 0)); }
}

@keyframes pulse-yellow {
  0% { opacity: 0.8; }
  50% { opacity: 1; }
  100% { opacity: 0.8; }
}
</style>
