import os

from src.bot.services.chart_game import GROWTH_VIDEO, render_growth_video

if __name__ == "__main__":
    # Рендер при запуске контейнера делит сервер с продом: процессы рендера и ffmpeg
    # наследуют пониженный приоритет.
    os.nice(10)
    render_growth_video(GROWTH_VIDEO)
    print(f"Ролик роста графика: {GROWTH_VIDEO}")
