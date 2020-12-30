import zipfile
import json
import os
import requests
import tempfile
import lxml.html
import shutil
from distutils.version import StrictVersion
from pyinfra.operations import apt, files, server


SHELL_EXTENSIONS_URL_LIST = [
    "https://extensions.gnome.org/extension/1160/dash-to-panel/",
    "https://extensions.gnome.org/extension/3628/arcmenu/",
    "https://extensions.gnome.org/extension/779/clipboard-indicator/",
]
SHELL_EXTENSION_URL_PATTERN = "https://extensions.gnome.org/extension-data/{extension_uuid}.v{extension_version}.shell-extension.zip"

# apt.update(
#     name='Update apt repositories',
#     cache_time=3600,
# )

# apt.packages(
#     packages=[
#         "vim",
#         "htop",
#         "atop",
#         "glances",
#         "gnome-tweak-tool",
#         "chrome-gnome-shell",
#         "curl",
#         "unzip",
#         "python3-lxml",
#         # "gnome-shell-extension-dash-to-panel",
#         # "gnome-shell-extension-arc-menu",
#         # "gnome-shell-extension-caffeine",
#     ]
# )


class ShellExtension:
    def __init__(self, name="", path_local="", url="") -> None:
        self.name = name
        self.path_local = path_local
        self.url = url
        self.extension_version = ""
        self.uuid = ""

    def get_uuid_local(self) -> None:
        with zipfile.ZipFile(self.path_local, "r") as archfile:
            metadata = json.loads(archfile.read("metadata.json").decode("utf-8"))
            self.uuid = metadata["uuid"]

    def _get_uuid_remote(self):
        r = requests.get(self.url, timeout=5)
        root = lxml.html.fromstring(r.content)
        data_element = root.xpath("//div[@data-uuid]")[0]
        self.uuid = data_element.get("data-uuid")

        data_smv_dict = json.loads(data_element.get("data-svm"))
        versions = list(data_smv_dict.keys())
        versions.sort(key=StrictVersion)
        max_gnome_version = versions[-1]
        self.extension_version = data_smv_dict[max_gnome_version]["version"]

    def _download(self) -> None:
        file_name = self.uuid.replace("@", "")
        self.path_local = os.path.join(tempfile.gettempdir(), f"{file_name}.zip")
        # files.download(
        #     src=SHELL_EXTENSION_URL_PATTERN.format(**{"extension_uuid": file_name, "extension_version": self.extension_version}),
        #     dest=self.path_local
        # )
        response = requests.get(SHELL_EXTENSION_URL_PATTERN.format(**{"extension_uuid": file_name, "extension_version": self.extension_version}), stream=True)
        with open(self.path_local, 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)

    def install(self) -> None:
        self._get_uuid_remote()
        user = os.getlogin()
        install_path = os.path.join("/home", user, ".local/share/gnome-shell/extensions", self.uuid)

        # if os.path.exists(install_path):
        #     return

        self._download()
        files.directory(path=install_path)
        with zipfile.ZipFile(self.path_local, "r") as archfile:
            archfile.extractall(install_path)

        # reset permissions
        server.shell(commands=[f"chown -R {user}:{user} {install_path}"])

        # activate
        server.shell(commands=[f"/usr/bin/gnome-extensions enable {self.uuid}"])

        os.unlink(self.path_local)


# dtp = ShellExtension(path_local="/home/e/Downloads/dash-to-paneljderose9.github.com.v40.shell-extension.zip")


for extension_url in SHELL_EXTENSIONS_URL_LIST:
    dtp = ShellExtension(url=extension_url)
    dtp.install()


# https://people.gnome.org/~federico/blog/alt-tab.html
# gsettings set org.gnome.desktop.wm.keybindings switch-applications "[]"
# gsettings set org.gnome.desktop.wm.keybindings switch-applications-backward "[]"
# gsettings set org.gnome.desktop.wm.keybindings switch-windows "['<Alt>Tab', '<Super>Tab']"
# gsettings set org.gnome.desktop.wm.keybindings switch-windows-backward  "['<Alt><Shift>Tab', '<Super><Shift>Tab']"

# gsettings set org.gnome.shell.window-switcher current-workspace-only true
