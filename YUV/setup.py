from setuptools import setup, find_packages

setup(name="yuv",
      version="1.0",
      license="GPLv2",
      description="This lib is used for YUV operations",
      keywords=["yuv", "tool"],
      author="Xueli Cheng",
      author_email="chengxl842363@gmail.com",
      packages=find_packages(),
      include_package_data=True,
      exclude_package_data={'': ['README.md']},
      platforms="Any"
      )
