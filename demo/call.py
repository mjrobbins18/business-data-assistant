"""Call the server's tools over real MCP (stdio), the same way Claude Desktop does. Appends each call to demo/calls.jsonl."""
import asyncio, json, sys
from pathlib import Path
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parents[1]

async def main(tool, args):
    params = StdioServerParameters(command="uv", args=["run", "--directory", str(ROOT), "python", "-m", "assistant.server"])
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        res = await s.call_tool(tool, args)
        out = res.structured_content if getattr(res, "structured_content", None) else [c.text for c in res.content]
        print(json.dumps(out, indent=1)[:4000])
        with (ROOT / "demo" / "calls.jsonl").open("a") as f:
            f.write(json.dumps({"tool": tool, "args": args, "result": out}) + "\n")

if __name__ == "__main__":
    tool = sys.argv[1]
    args = {"sql": sys.argv[2]} if tool == "run_query" else ({"table": sys.argv[2]} if tool == "describe_table" else {})
    asyncio.run(main(tool, args))
