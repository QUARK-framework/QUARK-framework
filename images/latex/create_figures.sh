#!/usr/bin/env bash

declare -a arr=("pipeline1" "pipeline2" "plugins")


cd "$(dirname "$0")"

for filename in "${arr[@]}"
do
    rm -rf out.tmp
    mkdir -p out.tmp
    cd out.tmp
    cp ../$filename.tex .
    pdflatex --shell-escape $filename.tex
    cd ..
    mv out.tmp/$filename.svg $filename.svg
    python delete_newlines.py $filename.svg
    mv $filename.svg ../$filename.svg
done
rm -rf out.tmp