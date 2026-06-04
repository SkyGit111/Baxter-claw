#!/bin/bash
# 清理并整理 debug 输出目录

echo "=========================================="
echo "清理和整理 Debug 输出目录"
echo "=========================================="
echo ""

# 创建统一的 debug 输出目录
mkdir -p debug_output/vlm
mkdir -p debug_output/grasp_verification
mkdir -p debug_output/archived

echo "[1/3] 创建统一目录结构..."
echo "  ✓ debug_output/vlm/"
echo "  ✓ debug_output/grasp_verification/"
echo "  ✓ debug_output/archived/"
echo ""

# 移动旧的 debug_vlm_* 目录
echo "[2/3] 移动旧的 VLM debug 目录..."
count=0
for dir in debug_vlm_*; do
    if [ -d "$dir" ]; then
        mv "$dir" debug_output/archived/
        count=$((count + 1))
    fi
done
echo "  ✓ 移动了 $count 个旧目录到 debug_output/archived/"
echo ""

# 移动旧的 debug/ 目录（如果存在）
echo "[3/3] 移动旧的 debug/ 目录..."
if [ -d "debug" ]; then
    mv debug/* debug_output/archived/ 2>/dev/null
    rmdir debug 2>/dev/null
    echo "  ✓ 已移动"
else
    echo "  - 不存在"
fi
echo ""

echo "=========================================="
echo "✓ 清理完成！"
echo "=========================================="
echo ""
echo "新的目录结构："
echo "  debug_output/"
echo "    ├── vlm/              (VLM 定位和深度图)"
echo "    ├── grasp_verification/  (抓取验证图片)"
echo "    └── archived/         (旧的 debug 文件)"
echo ""
echo "旧文件已移动到: debug_output/archived/"
echo ""
