#!/bin/bash
python -m cProfile -o $1.prof $1
python -c "import pstats; s = pstats.Stats('$1.prof'); s.sort_stats('cumulative').print_stats()"
