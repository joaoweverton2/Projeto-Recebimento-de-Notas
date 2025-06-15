from setuptools import setup, find_packages

setup(
    name="projeto-recebimento-de-notas",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "Flask==3.0.0",
        "pandas==1.5.3",
        "Flask-SQLAlchemy==3.1.1",
        "Flask-Migrate==4.0.5",
        "python-dotenv==1.0.0",
        "numpy==1.23.5"
    ],
    python_requires='>=3.11',
)