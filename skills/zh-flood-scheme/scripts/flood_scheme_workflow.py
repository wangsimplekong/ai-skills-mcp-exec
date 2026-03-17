#!/usr/bin/env python3
"""
漳河洪水预报方案计算工作流执行脚本

Usage:
    python flood_scheme_workflow.py --token <JWT_TOKEN> --start <YYYY-MM-DD HH:MM:SS> --end <YYYY-MM-DD HH:MM:SS> --message "<分析需求>"

输出:
    JSON 格式的工作流执行结果，包含各节点输出和最终分析结论
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, Optional


class MCPWorkflowExecutor:
    """MCP 工作流执行器"""
    
    def __init__(self, token: str, server: str = "Evangelion-mcp-zh-flood"):
        self.token = token
        self.server = server
        self.service_token: Optional[str] = None
        self.project_id = "a111a90847aa4a75a885c3ad14d8a91a"
        
    def _call_mcp_tool(self, tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """调用 MCP 工具"""
        cmd = ["mcporter", "call", f"{self.server}.{tool}"]
        for key, value in args.items():
            if isinstance(value, dict):
                cmd.append(f"{key}={json.dumps(value)}")
            else:
                cmd.append(f"{key}={value}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                return {"success": False, "error": result.stderr, "tool": tool}
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout", "tool": tool}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"JSON parse error: {e}", "tool": tool}
    
    def _extract_service_token(self, query_result: Dict) -> Optional[str]:
        """从查询结果中提取 serviceToken"""
        try:
            data = query_result.get("execute", {}).get("params", {}).get("queryCreateParamResult", "")
            if data:
                # serviceToken 在后续调用中由服务器维护，不需要显式传递
                return "extracted"
        except Exception:
            pass
        return None
    
    def execute_workflow(self, start_date: str, end_date: str, message: str) -> Dict[str, Any]:
        """
        执行完整的洪水预报方案计算工作流
        
        三阶段:
        1. buildSchemeCalculation - 构建预报方案
        2. callSchemeCalculation - 执行方案计算
        3. getModelStatisticsOfIndicators - 获取预报成果分析
        """
        workflow_result = {
            "workflow": "zh-flood-scheme",
            "start_time": datetime.now().isoformat(),
            "nodes": {},
            "final_result": None,
            "error": None
        }
        
        # ========== 阶段 1: 构建预报方案 ==========
        print(f"[1/3] 构建预报方案 ({start_date} ~ {end_date})...")
        build_args = {
            "token": self.token,
            "startDate": start_date,
            "endDate": end_date,
            "message": message
        }
        build_result = self._call_mcp_tool("buildSchemeCalculation", build_args)
        workflow_result["nodes"]["buildSchemeCalculation"] = build_result
        
        if not build_result.get("success") and not build_result.get("execute", {}).get("params", {}).get("calculateResult"):
            # 检查是否是部分成功（有 calculateResult 说明流程已执行）
            if "calculateResult" not in str(build_result):
                workflow_result["error"] = f"阶段 1 失败：{build_result.get('error', 'Unknown error')}"
                workflow_result["end_time"] = datetime.now().isoformat()
                return workflow_result
        
        # 从构建结果中提取关键数据用于后续调用
        execute_params = build_result.get("execute", {}).get("params", {})
        
        # ========== 阶段 2: 执行方案计算 ==========
        print("[2/3] 执行方案计算...")
        
        # 构建 callSchemeCalculation 的参数（复用阶段 1 的结果）
        call_args = {
            "token": self.token,
            "buildSearchParam": json.dumps({
                "queryCreateParamResult": execute_params.get("queryCreateParamResult", ""),
                "createNewSchemeResult": execute_params.get("createNewSchemeResult", ""),
                "weightCoefficientResult": execute_params.get("weightCoefficientResult", ""),
                "queryParamDataResult": execute_params.get("queryParamDataResult", ""),
                "calculateResult": execute_params.get("calculateResult", '{"success":true}'),
                "resultArealRainFallResult": execute_params.get("resultArealRainFallResult", ""),
            })
        }
        call_result = self._call_mcp_tool("callSchemeCalculation", call_args)
        workflow_result["nodes"]["callSchemeCalculation"] = call_result
        
        # ========== 阶段 3: 获取预报成果分析 ==========
        print("[3/3] 获取预报成果分析...")
        
        # 构建 getModelStatisticsOfIndicators 的参数
        stats_args = {
            "token": self.token,
            "calculationData": json.dumps({
                "execute": False,
                "params": {
                    "token": self.token,
                    "projectId": self.project_id,
                    "startDate": start_date,
                    "endDate": end_date,
                    "queryCreateParamResult": execute_params.get("queryCreateParamResult", ""),
                    "createNewSchemeResult": execute_params.get("createNewSchemeResult", ""),
                    "weightCoefficientResult": execute_params.get("weightCoefficientResult", ""),
                    "queryParamDataResult": execute_params.get("queryParamDataResult", ""),
                    "calculateResult": execute_params.get("calculateResult", '{"success":true}'),
                    "resultArealRainFallResult": execute_params.get("resultArealRainFallResult", ""),
                    "resultArealRainFallMdResult": execute_params.get("resultArealRainFallMdResult", ""),
                }
            }),
            "forecastUnitTypeCode": "10000"  # 漳河水库
        }
        stats_result = self._call_mcp_tool("getModelStatisticsOfIndicators", stats_args)
        workflow_result["nodes"]["getModelStatisticsOfIndicators"] = stats_result
        
        # ========== 提取关键指标 ==========
        workflow_result["final_result"] = self._extract_key_indicators(stats_result)
        workflow_result["end_time"] = datetime.now().isoformat()
        
        return workflow_result
    
    def _extract_key_indicators(self, stats_result: Dict) -> Dict[str, Any]:
        """从统计结果中提取关键指标"""
        indicators = {
            "success": False,
            "rainfall": {},
            "peak_flow": {},
            "flow_process": [],
            "reservoir_levels": {}
        }
        
        try:
            params = stats_result.get("execute", {}).get("params", {})
            
            # 提取降雨统计
            rain_result = params.get("resultArealRainFallResult", "")
            if rain_result:
                try:
                    rain_data = json.loads(rain_result).get("data", {}).get("statistical", [])
                    for item in rain_data:
                        indicators["rainfall"][item["name"]] = item["value"]
                except Exception:
                    pass
            
            # 提取流量过程和峰现时间
            object_process = params.get("getObjectProcessDataTableResult", "")
            if object_process:
                try:
                    process_data = json.loads(object_process)
                    chart_data = process_data.get("data", {}).get("chart", {}).get("chartDataList", [])
                    
                    # 查找最大流量和时间
                    for data_series in chart_data:
                        if data_series.get("key") == "10000:ADJUST_RUNOFF":  # 校正流量
                            values = data_series.get("value", [])
                            times = []
                            for ts in chart_data:
                                if ts.get("key") == "time":
                                    times = ts.get("value", [])
                                    break
                            
                            if values and times:
                                max_flow = 0
                                peak_time = ""
                                for i, v in enumerate(values[:120]):  # 只看前 5 天
                                    try:
                                        flow = float(v) if v else 0
                                        if flow > max_flow:
                                            max_flow = flow
                                            peak_time = times[i] if i < len(times) else ""
                                    except ValueError:
                                        continue
                                
                                indicators["peak_flow"] = {
                                    "value": max_flow,
                                    "time": peak_time,
                                    "unit": "m³/s"
                                }
                except Exception:
                    pass
            
            # 提取水库特征水位
            if object_process:
                try:
                    process_data = json.loads(object_process)
                    data_map = process_data.get("data", {}).get("dataMap", {})
                    indicators["reservoir_levels"] = {
                        "FLOOD_RESISTRAIN": data_map.get("FLOOD_RESISTRAIN", ""),  # 防洪限制水位
                        "DESIGN_RESISTRAIN": data_map.get("DESIGN_RESISTRAIN", ""),  # 设计洪水位
                        "HIGHFLOOD_RESISTRAIN": data_map.get("HIGHFLOOD_RESISTRAIN", ""),  # 高洪水位
                        "CHECK_RESISTRAIN": data_map.get("CHECK_RESISTRAIN", ""),  # 校核洪水位
                    }
                except Exception:
                    pass
            
            indicators["success"] = True
            
        except Exception as e:
            indicators["error"] = str(e)
        
        return indicators


def main():
    parser = argparse.ArgumentParser(description="漳河洪水预报方案计算工作流执行器")
    parser.add_argument("--token", required=True, help="JWT Token")
    parser.add_argument("--start", required=True, help="开始时间 (YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--end", required=True, help="结束时间 (YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--message", default="洪水预报分析", help="分析需求描述")
    parser.add_argument("--output", "-o", help="输出文件路径 (默认输出到 stdout)")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    # 执行工作流
    executor = MCPWorkflowExecutor(token=args.token)
    result = executor.execute_workflow(
        start_date=args.start,
        end_date=args.end,
        message=args.message
    )
    
    # 输出结果
    output_json = json.dumps(result, ensure_ascii=False, indent=2)
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"结果已保存到：{args.output}")
    else:
        print(output_json)
    
    # 返回状态码
    sys.exit(0 if result.get("final_result", {}).get("success") else 1)


if __name__ == "__main__":
    main()
