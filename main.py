import os
import pathlib
import tarfile

import requests
import toml
from bs4 import BeautifulSoup
from pathlib import Path

# def get_installed_filepaths(include_dict: dict) -> list[str]:

CPP_FILE_EXTENSIONS = (".c", ".cpp", ".h", ".hpp", ".cc", ".C", ".hxx", ".cxx")

XBUILD_PATH = Path.home() / "XBuild"
XBUILD_LIBRARY_PATH = XBUILD_PATH / "libraries"

if not os.path.exists(XBUILD_LIBRARY_PATH):
    os.makedirs(XBUILD_LIBRARY_PATH)


def is_test(version_str: str) -> bool:
    test_values = ("test", "example", "TEST", "EXAMPLE", "Test", "Example")
    if any(x in version_str for x in test_values):
        return True
    return False


def generate_cppget_url(dependency, desired_version) -> list[str] | str | None:
    response = BeautifulSoup(
        requests.get(f"https://pkg.cppget.org/1/stable/{dependency}/").text,
        "html.parser"
    )
    rows = response.find_all("tr")[3:-1]
    row_values = [row.find_all("td")[1] for row in rows]

    available_versions = [
        version.string for version in row_values
        if desired_version in version.string and not is_test(version.string)
    ]

    # print(available_versions)
    if len(available_versions) > 1:
        return available_versions
    elif len(available_versions) == 1:
        return available_versions[0]

    raise Exception(f"Version {desired_version} unavailable")


def find_and_install(dependency: str, version: str) -> Path | list[Path]:
    url_or_url_list = generate_cppget_url(dependency, version)
    dependency_location = XBUILD_LIBRARY_PATH / dependency
    tarball_filename = dependency_location / (version + ".tar.gz")

    if url_or_url_list is not None:
        if isinstance(url_or_url_list, str):
            download_format_package(dependency, dependency_location, tarball_filename, url_or_url_list)
            return dependency_location / url_or_url_list[:-7]
        elif isinstance(url_or_url_list, list):
            filepaths = []
            for url in url_or_url_list:
                download_format_package(dependency, dependency_location, tarball_filename, url)
                filepaths.append(dependency_location / url)

            return filepaths


def download_format_package(dependency, dependency_location, tarball_filename, url):
    print("Downloading", url[:-7])
    response = requests.get(
        f"https://pkg.cppget.org/1/stable/{dependency}/{url}",
        stream=True
    )
    if not os.path.exists(dependency_location):
        os.makedirs(dependency_location)
    with open(tarball_filename, "wb") as f:
        f.write(response.raw.read())
    with tarfile.open(tarball_filename) as tf:
        tf.extractall(dependency_location)
    os.remove(tarball_filename)


def write_lock_file(toml_filepath: str | Path = "./xbuild.toml"):
    if isinstance(toml_filepath, str):
        toml_filepath = Path(toml_filepath)

    # print(toml_filepath.parent)
    lockfile_path = toml_filepath.parent / "xbuild.lock"
    print(lockfile_path)

    built_dict = build_lock_file(toml_filepath)

    with open(lockfile_path, "w+") as lockfile:
        toml.dump(built_dict, lockfile)


def build_lock_file(toml_filepath: Path) -> dict:
    # Filepath structure libraries/library-names/version-numbers/installations
    toml_data = toml.load(toml_filepath)

    res = {"dependencies": {}}

    xbuild_data = toml_data["xbuild"]
    platform_data = toml_data["platform"]

    downloaded_libraries = {}
    lib_path = XBUILD_PATH / "libraries"
    for library_folder in os.listdir(lib_path):
        sub_path = lib_path / library_folder
        if os.path.isdir(sub_path):
            downloaded_libraries[library_folder] = set(
                file for file in os.listdir(sub_path) if os.path.isdir(sub_path / file)
            )

    for dependency, version in xbuild_data["dependencies"].items():
        if dependency in downloaded_libraries and version in downloaded_libraries[dependency]:
            # already have the library installed
            res["dependencies"][dependency]["location"] = lib_path / dependency / version
        else:
            res["dependencies"][dependency]["location"] = find_and_install(dependency, version)




def build(in_file: str, out_file: str, compiler: str = "gcc"):
    xbuild_file = "xbuild.toml"

    toml_data = toml.load(xbuild_file)

    xbuild_data = toml_data["xbuild"]
    platform_data = toml_data["platform"]

    print(xbuild_data)
    # format = {libname: version, libname: version, etc.}
    include_dict = xbuild_data["dependencies"]

    # Find the right version of the library in xbuild root


    # include_string = " ".join(include_paths)
    # os.system(f"cmd /c {compiler} {in_file} -o {out_file} -I {include_string}")