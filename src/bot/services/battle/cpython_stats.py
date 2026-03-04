import pstats

# Загрузка данных
stats = pstats.Stats("output.pstats")
# Сортировка по общему времени (tottime) или накопленному времени (cumulative)
stats.sort_stats("cumulative").print_stats(20)  # 20 - количество строк
