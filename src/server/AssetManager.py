import os
import json

class AssetException(Exception):
    pass


class AssetManager:
    ASSET_KINDS = ["ships", "weapons"]

    def __init__(self, asset_dirs):
        self.asset_dirs = asset_dirs
        self.assets = {k: {} for k in AssetManager.ASSET_KINDS}
        self.load()

    def load(self):
        print("Loading")
        for dir in self.asset_dirs:
            print("Dir", dir)
            for kind in AssetManager.ASSET_KINDS:
                print("Kind", kind)
                for path, dirs, files in os.walk(os.path.join(dir, kind)):
                    print("Files", files)
                    for file in files:
                        print("Full Paths", os.path.join(dir, kind, file))
                        with open(os.path.join(dir, kind, file)) as f:
                            loaded = json.load(f)
                            name = os.path.splitext(os.path.basename(file))[0]
                            print(name)
                            self.assets[kind][name] = loaded
                    break
                    

    def find_asset(self, kind, name):
        if kind not in AssetManager.ASSET_KINDS:
            raise AssetException(kind + " is not an asset type")
        if name in self.assets[kind]:
            return self.assets[kind][name]
        return None
