class Config:
    path_to_assets = "/assets"
    path_to_gif = path_to_assets + "/animation"
    path_to_video = path_to_assets + "/video"
    path_to_photo = path_to_assets + "/photo"
    path_to_kagune_gif = path_to_gif + "/kagune"
    path_to_snap_gif = path_to_gif + "/snap"

    allowed_kagune_folders = ["ukaku", "koukaku", "rinkaku", "bikaku"]

    def get_kagune_gif_folder(self, kagune_name: str):
        if kagune_name not in self.allowed_kagune_folders:
            return None

        return self.path_to_kagune_gif + kagune_name


game_config = Config()
