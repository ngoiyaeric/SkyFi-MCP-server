#!/usr/bin/env python3
"""
Fix commented-out tool decorators in the MCP server.
"""

import re
import glob
from pathlib import Path

def fix_commented_tools():
    """Uncomment all @*_mcp.tool decorators in the codebase."""
    
    # Find all Python files in service modules
    patterns = [
        "src/mcp_skyfi/skyfi/*.py",
        "src/mcp_skyfi/osm/*.py", 
        "src/mcp_skyfi/weather/*.py"
    ]
    
    files_to_fix = []
    for pattern in patterns:
        files_to_fix.extend(glob.glob(pattern))
    
    # Regex patterns to match commented tool decorators
    patterns_to_fix = [
        (r'^# @(skyfi_mcp|osm_mcp|weather_mcp)\.tool\(', r'@\1.tool('),
        (r'^#     name=', r'    name='),
        (r'^#     description=', r'    description='),
        (r'^# \)', r')')
    ]
    
    total_fixes = 0
    
    for file_path in files_to_fix:
        path = Path(file_path)
        if not path.exists():
            continue
            
        print(f"🔧 Checking {file_path}...")
        
        # Read file content
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")
            continue
        
        original_content = content
        file_fixes = 0
        
        # Apply all pattern fixes
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            fixed_line = line
            for pattern, replacement in patterns_to_fix:
                if re.match(pattern, line):
                    fixed_line = re.sub(pattern, replacement, line)
                    if fixed_line != line:
                        file_fixes += 1
                        print(f"  ✅ Fixed: {line.strip()} -> {fixed_line.strip()}")
                    break
            fixed_lines.append(fixed_line)
        
        if file_fixes > 0:
            # Write back the fixed content
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(fixed_lines))
                print(f"  📝 Wrote {file_fixes} fixes to {file_path}")
                total_fixes += file_fixes
            except Exception as e:
                print(f"❌ Error writing {file_path}: {e}")
        else:
            print(f"  ℹ️ No fixes needed in {file_path}")
    
    print(f"\n🎉 Total fixes applied: {total_fixes}")
    return total_fixes

if __name__ == "__main__":
    fix_commented_tools()