from setuptools import setup, find_packages


def scm_version():
    def local_scheme(version):
        return version.format_choice("+{node}", "+{node}.dirty")
    return {
        "relative_to": __file__,
        "version_scheme": "guess-next-dev",
        "local_scheme": local_scheme,
    }


setup(
    name="utmi",
    use_scm_version=scm_version(),
    author="Aled Cuda",
    author_email="aledvirgil@gmail.com",
    description="FPGA portion of the VLSIR UTMI Phy",
    license="BSD",
    setup_requires=["wheel", "setuptools", "setuptools_scm"],
    python_requires=">=3.7",
    install_requires=[
        "amaranth>=0.2",
    ],
    packages=find_packages(),
    project_urls={
        "Source Code": "https://github.com/Vlsir/Usb2Phy",
        "Bug Tracker": "https://github.com/Vlsir/Usb2Phy",
    },
)
