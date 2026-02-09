
    def check_service_status(self, service_name: str) -> str:
        """Check systemd service status"""
        try:
            self.connect()
            status = self.execute_command(f"systemctl is-active {service_name}")
            status = status.strip() if status else "unknown"
            
            if status == "active":
                return "active"
            elif status in ("inactive", "dead"):
                return "inactive"
            elif status in ("failed", "error"):
                return "error"
            else:
                return "stopped"
        except Exception as e:
            logger.error(f"Service status check failed: {e}")
            return "stopped"
        finally:
            self.close()

    def collect_mysql_metrics(self, port: int, username: str, password: str = None) -> Dict[str, any]:
        """Collect MySQL metrics using mysqladmin"""
        try:
            self.connect()
            pass_arg = f"-p'{password}'" if password else ""
            # Try multiple paths for mysqladmin
            cmds = ["mysqladmin", "/usr/bin/mysqladmin", "/usr/local/mysql/bin/mysqladmin"]
            output = ""
            for binary in cmds:
                cmd = f"{binary} -u{username} {pass_arg} -P{port} -h127.0.0.1 status"
                try:
                    output = self.execute_command(cmd)
                    if output and "Uptime" in output:
                        break
                except Exception:
                    continue
            
            metrics = {}
            if output:
                import re
                uptime = re.search(r'Uptime:\s+(\d+)', output)
                if uptime: metrics['uptime'] = int(uptime.group(1))
                
                threads = re.search(r'Threads:\s+(\d+)', output)
                if threads: metrics['threads'] = int(threads.group(1))
                
                open_tables = re.search(r'Open tables:\s+(\d+)', output)
                if open_tables: metrics['open_tables'] = int(open_tables.group(1))
                
                qps = re.search(r'Queries per second avg:\s+([\d\.]+)', output)
                if qps: metrics['qps'] = float(qps.group(1))
                
                # Backwards compatibility
                metrics['queries_per_second_avg'] = metrics.get('qps')
            return metrics
        except Exception as e:
            logger.error(f"MySQL metrics collection failed: {e}")
            return {}
        finally:
            self.close()

    def collect_redis_metrics(self, port: int, password: str = None) -> Dict[str, any]:
        """Collect Redis metrics using redis-cli"""
        try:
            self.connect()
            auth_arg = f"-a '{password}'" if password else ""
            # Try multiple paths for redis-cli
            cmds = ["redis-cli", "/usr/bin/redis-cli", "/usr/local/bin/redis-cli"]
            output = ""
            for binary in cmds:
                cmd = f"{binary} -h 127.0.0.1 -p {port} {auth_arg} info"
                try:
                    output = self.execute_command(cmd)
                    if output and ("redis_version" in output or "connected_clients" in output):
                        break
                except Exception:
                    continue

            metrics = {}
            if output:
                for line in output.splitlines():
                    if ':' in line:
                        key, val = line.split(':', 1)
                        key = key.strip()
                        val = val.strip()
                        if key == "connected_clients":
                            metrics["connected_clients"] = int(val)
                        elif key == "instantaneous_ops_per_sec":
                            metrics["instantaneous_ops_per_sec"] = int(val)
                        elif key == "used_memory_human":
                            metrics["used_memory_human"] = val
                        elif key == "uptime_in_seconds":
                            metrics["uptime_in_seconds"] = int(val)
            return metrics
        except Exception as e:
            logger.error(f"Redis metrics collection failed: {e}")
            return {}
        finally:
            self.close()

    def get_metrics_and_status(self, mw_type: str, port: int, service_name: str, username: str = None, password: str = None) -> Dict[str, any]:
        """Collect both status and metrics in a single SSH session"""
        result = {"status": "unknown"}
        try:
            self.connect()
            
            # 1. Check Status
            if service_name:
                try:
                    status_out = self.execute_command(f"systemctl is-active {service_name}")
                    status_out = status_out.strip() if status_out else "unknown"
                    if status_out == "active":
                        result["status"] = "active"
                    elif status_out in ("inactive", "dead"):
                        result["status"] = "inactive"
                    elif status_out in ("failed", "error"):
                        result["status"] = "error"
                    else:
                        result["status"] = "stopped"
                except Exception as e:
                    logger.warning(f"Status check failed: {e}")
                    result["status"] = "stopped"
            else:
                result["status"] = "active" # Assume active if no service name

            # 2. Collect Metrics if active
            if result["status"] == "active":
                metrics = {}
                # Reuse connection for metrics
                # Since we are already connected, we can't call collect_mysql_metrics because it calls connect() again
                # We need inline logic or separated logic. 
                # To be safe and simple: implemented inline logic below reusing self.client
                
                if mw_type == 'mysql':
                    pass_arg = f"-p'{password}'" if password else ""
                    cmds = ["mysqladmin", "/usr/bin/mysqladmin", "/usr/local/mysql/bin/mysqladmin"]
                    output = ""
                    for binary in cmds:
                        cmd = f"{binary} -u{username} {pass_arg} -P{port} -h127.0.0.1 status"
                        try:
                            # Direct execute_command call reused
                            stdin, stdout, stderr = self.client.exec_command(cmd)
                            out_str = stdout.read().decode('utf-8').strip()
                            if out_str and "Uptime" in out_str:
                                output = out_str
                                break
                        except Exception:
                            continue
                    
                    if output:
                        import re
                        uptime = re.search(r'Uptime:\s+(\d+)', output)
                        if uptime: metrics['uptime'] = int(uptime.group(1))
                        
                        threads = re.search(r'Threads:\s+(\d+)', output)
                        if threads: metrics['threads'] = int(threads.group(1))
                        
                        open_tables = re.search(r'Open tables:\s+(\d+)', output)
                        if open_tables: metrics['open_tables'] = int(open_tables.group(1))
                        
                        qps = re.search(r'Queries per second avg:\s+([\d\.]+)', output)
                        if qps: metrics['qps'] = float(qps.group(1))
                        metrics['queries_per_second_avg'] = metrics.get('qps')
                
                elif mw_type == 'redis':
                    auth_arg = f"-a '{password}'" if password else ""
                    cmds = ["redis-cli", "/usr/bin/redis-cli", "/usr/local/bin/redis-cli"]
                    output = ""
                    for binary in cmds:
                        cmd = f"{binary} -h 127.0.0.1 -p {port} {auth_arg} info"
                        try:
                            stdin, stdout, stderr = self.client.exec_command(cmd)
                            out_str = stdout.read().decode('utf-8').strip()
                            if out_str and ("redis_version" in out_str or "connected_clients" in out_str):
                                output = out_str
                                break
                        except Exception:
                            continue

                    if output:
                        for line in output.splitlines():
                            if ':' in line:
                                key, val = line.split(':', 1)
                                key = key.strip()
                                val = val.strip()
                                if key == "connected_clients":
                                    metrics["connected_clients"] = int(val)
                                elif key == "instantaneous_ops_per_sec":
                                    metrics["instantaneous_ops_per_sec"] = int(val)
                                elif key == "used_memory_human":
                                    metrics["used_memory_human"] = val
                                elif key == "uptime_in_seconds":
                                    metrics["uptime_in_seconds"] = int(val)
                
                result.update(metrics)
                
            return result
            
        except Exception as e:
            logger.error(f"Combined metrics collection failed: {e}")
            return result
        # finally block in upper caller handles close? No, function should close.
        # But wait, self.connect() was called at start. 
        # If we return, we must close.
        finally:
            self.close()
