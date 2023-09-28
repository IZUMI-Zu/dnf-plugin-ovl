"""Package setup script for drv-img."""

from setuptools import setup, find_packages
import drv_img


def long_description():
    """
    Return the contents of the 'README.md' file as a string.

    :return: the contents of 'README.md' file
    :rtype: str
    """
    with open('README.md', encoding='utf-8') as file:
        return file.read()


setup(
    name=drv_img.__cli_name__,
    version=drv_img.__version__,
    description=drv_img.__doc__.strip(),
    long_description=long_description(),
    long_description_content_type='text/markdown',
    author=drv_img.__author__,
    author_email='binshuozu@gmail.com',
    license=drv_img.__license__,
    packages=find_packages(include=['drv_img', 'drv_img.*']),
    entry_points={
        'console_scripts': [
            'drv-img = drv_img.run:main',
        ],
    },
    python_requires='>=3.7',
    install_requires=["rpm"],
)
