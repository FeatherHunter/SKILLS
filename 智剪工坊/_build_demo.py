#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build timeline-demo.html"""
import os

OUT = "timeline-demo.html"

with open(OUT, "w", encoding="utf-8") as f:
    f.write("<!DOCTYPE html>\n<html lang=\"zh-CN\"><head><meta charset=\"UTF-8\">\n")
    f.write("<title>智剪工坊 v1.15 DEMO - Timeline Editor</title>\n")
    # Write CSS
    with open("_demo_css.txt", "r", encoding="utf-8") as css:
        f.write("<style>\n")
        f.write(css.read())
        f.write("\n</style>\n")
    f.write("</head><body>\n")
    # Write HTML body
    with open("_demo_body.txt", "r", encoding="utf-8") as body:
        f.write(body.read())
    # Write JS
    with open("_demo_js.txt", "r", encoding="utf-8") as js:
        f.write("\n<script>\n")
        f.write(js.read())
        f.write("\n</script>\n")
    f.write("\n</body></html>")

size = os.path.getsize(OUT)
print(f"Generated {OUT}: {size} bytes")
