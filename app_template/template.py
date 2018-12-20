import os
import sys

from collections import defaultdict

CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))

def fillin_template(template, project_name, project_title):
    template = template.replace("{project}", project_name.lower())
    template = template.replace("{Project}", project_name.title())
    template = template.replace("{PROJECT}", project_name.upper())
    template = template.replace("{Project-Title}", project_title)
    return template

def write_webapp_templates(project_name, project_title):

    basenames = [
        "admin.py",
        "apps.py",
        "constants.py",
        "displayer.py",
        "forms.py",
        "meta_parameters.py",
        "models.py",
        "parser.py",
        "submit.py",
        "urls.py",
        "views.py",
        "migrations/__init__.py",
        "tests/__init__.py",
        "tests/test_views.py",
        "tests/outputs.json",
    ]

    new_files = defaultdict(str)
    for basename in basenames:
        with open(os.path.join(CURRENT_PATH, "project", basename)) as f:
            template = f.read()
        template = fillin_template(template, project_name, project_title)
        new_files[basename] = template

    destination_dir = os.path.join(CURRENT_PATH, "..", "webapp", "apps",
                                "projects", project_name.lower())
    os.mkdir(destination_dir)
    os.mkdir(os.path.join(destination_dir, "tests"))
    os.mkdir(os.path.join(destination_dir, "migrations"))


    for basename, text in new_files.items():
        with open(os.path.join(destination_dir, basename), "w") as f:
            f.write(text)


def write_distributed_templates(project_name, project_title):
    new_files = defaultdict(str)
    with open(os.path.join(CURRENT_PATH, "project", "distributed",
                           "{project}_tasks.py")) as f:
        template = f.read()
    taskfile = fillin_template(template, project_name, project_title)
    outpath = os.path.join(CURRENT_PATH, "..", "distributed", "api",
                           "celery_app",
                           f"{project_name}_tasks.py")
    new_files[outpath] = taskfile

    with open(os.path.join(CURRENT_PATH, "project", "distributed",
                           "Dockerfile")) as f:
        template = f.read()
    dockerfile = fillin_template(template, project_name, project_title)
    outpath = os.path.join(CURRENT_PATH, "..", "distributed", "dockerfiles",
                              "projects", f"Dockerfile.{project_name}_tasks")
    new_files[outpath] = dockerfile

    for outpath, text in new_files.items():
        with open(outpath, "w") as f:
            f.write(text)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise ValueError("No project name specified")

    project_name = sys.argv[1]
    project_title = sys.argv[2]
    write_webapp_templates(project_name, project_title)
    write_distributed_templates(project_name, project_title)