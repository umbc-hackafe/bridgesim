from ClientAPI import BaseContext, expose
import os
class AssetManager:
    class Context(BaseContext):
        pass

    ASSET_DIRS = (os.path.join(os.getcwd(), "../../assets"),
                  "/usr/share/bridgesim/assets",
                  "/usr/local/share/bridgesim/assets",
                  os.path.expanduser("~/.bridgesim/assets"),
              )

    ASSET_TYPES = ("data", "models", "scenarios")
    ASSET_SUBTYPES = {"data": ("ships", "missile", "station", "entity")}

    def __init__(self):
        self.reload()


    def reload(self):
        for assetDir in [d for d in self.ASSET_DIRS if os.path.exists(d)]:
            print("Checking for assets in {}...".format(assetDir))
            for assetType in self.ASSET_TYPES:
                print("Checking for {} assets...".format(assetType))
                assetTypeDir = os.path.join(assetDir, assetType)
                if assetType in self.ASSET_SUBTYPES:
                    subtypeDirs = [os.path.join(assetTypeDir, d) for d in self.ASSET_SUBTYPES[assetType]]
                else:
                    subtypeDirs = [assetTypeDir]
                for finalDir in [d for d in subtypeDirs if os.path.exists(d)]:
                    print("... Checking in {}...".format(finalDir))
                    for assetFile in [f for f in os.listdir(finalDir) if os.path.isfile(os.path.join(finalDir, f))]:
                        print("Found '{}' asset file: {}".format(assetType, assetFile))
