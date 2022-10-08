import datetime
import subprocess
import sys

import packaging.version
from pathlib import Path
import git
import requests
import tomli
import logging

logging.basicConfig(level=logging.INFO)

from github import Github


class BumpRelease:
    def __init__(self):
        self.session = requests.Session()

        self.version_file = Path(self.get_git_root(__file__), "pyproject.toml")
        assert self.version_file.is_file(), "Could not find pyproject.toml"

        self.toml = tomli.loads(self.version_file.read_text())
        self.current_version = packaging.version.parse(self.toml["tool"]["poetry"]["version"])
        assert self.current_version, "Could not find version in pyproject.toml"

        self.branch = self.get_branch()
        self.github = Github().get_repo(self.get_repo())

        self.latest_release = self.github.get_latest_release()

        self.latest_github_release_version = packaging.version.parse(self.latest_release.tag_name)

        if self.branch == self.github.default_branch:
            self.pypi_json = self.session.get("https://pypi.org/pypi/sickchill/json").json()
            assert self.pypi_json, "Could not get pypi json"

            self.current_pypi_version = packaging.version.parse(self.pypi_json["info"]["version"])

            if self.current_pypi_version != self.current_version:
                logging.warning("Current version does not match pypi version")
            if self.current_version != self.latest_github_release_version:
                logging.warning("Current version does not match latest github release version")

        self.bump_version()

    def next_version(self):
        today = datetime.date.today().strftime("%Y.%-m.%-d")

        if self.branch == self.github.default_branch:
            if datetime.datetime.strptime(today, "%Y.%m.%d") > datetime.datetime.strptime(self.current_version.base_version, "%Y.%m.%d"):
                return f"{today}"

            num = (self.current_version.post or 0) + 1
            return f"{self.current_version.base_version}-post{num}"

        elif self.branch == "develop":
            if datetime.datetime.strptime(today, "%Y.%m.%d") > datetime.datetime.strptime(self.current_version.base_version, "%Y.%m.%d"):
                return f"{today}.dev0"
            num = (self.current_version.dev or 0) + 1
            return f"{self.current_version.base_version}-dev{num}"

    def bump_version(self):
        if "-n" in sys.argv:
            print(self.next_version())
        else:
            subprocess.check_call(["poetry", "version", self.next_version()])

    @staticmethod
    def get_git_root(path):
        return git.Repo(path, search_parent_directories=True).git.rev_parse("--show-toplevel")

    def get_repo(self):
        root = git.Repo(self.get_git_root(__file__))
        remote = str(root.git.remote("get-url", "--push", "origin"))
        return remote.replace("git@github.com:", "").replace(".git", "").replace("https://github.com/", "")

    def get_branch(self):
        return git.Repo(self.get_git_root(__file__)).active_branch.name

    def write_json_to_file(self, filename):
        with open(filename, "w") as f:
            f.write(self.pypi_json)


BumpRelease()
