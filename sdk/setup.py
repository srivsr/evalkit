from setuptools import setup, find_packages

setup(
    name="evalkit",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.26.0",
    ],
    python_requires=">=3.9",
    author="EvalKit",
    author_email="support@evalkit.dev",
    description="Python SDK for EvalKit RAG Evaluation Platform",
    long_description=open("README.md").read() if __import__("os").path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    url="https://github.com/evalkit/evalkit-python",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
