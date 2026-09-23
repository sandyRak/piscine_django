import sys
import os
import re

def error_exit(msg):
    """Affiche un message d'erreur sur stderr et quitte proprement."""
    print("Error: {}".format(msg), file=sys.stderr)
    sys.exit(1)

def check_file(argv):
  if len(argv) != 2:
    error_exit("usage: python3 render.py <file.template>")
  if not os.path.exists(argv[1]):
    error_exit("'{}' does not exist or is not a file".format(argv[1]))
  if not argv[1].endswith(".template"):
      error_exit("'{}' must have a .template extension".format(argv[1]))
  return(argv[1])

def load_settings(settings_file):
  if not os.path.isfile(settings_file):
    error_exit("settings file '{}' not found".format(settings_file))
  try:
    with open(settings_file, "r") as f:
      source = f.read()
  except Exception as e:
    error_exit("could not read '{}': {}".format(settings_file, e))
  settings = {}
  try:
    exec(source, settings)
  except Exception as e:
    error_exit("could not evaluate '{}': {}".format(settings_file, e))
  return settings

def load_template(template_file):
  try:
    with open(template_file, "r") as f:
      template = f.read()
  except Exception as e:
    error_exit("could not read '{}':{}".format(template_file, e))
  return template


def render(content, settings):
    """Remplace les motifs {variable} par leur valeur dans settings."""
    pattern = re.compile(r"\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}")
 
    def replace(match):
        key = match.group(1)
        if key not in settings:
            error_exit("variable '{}' is not defined in settings.py".format(key))
        return str(settings[key])
 
    return pattern.sub(replace, content)
 
 
def write_html(filepath, content):
    """Écrit le résultat dans un fichier .html de même nom."""
    html_path = os.path.splitext(filepath)[0] + ".html"
    try:
        with open(html_path, "w") as f:
            f.write(content)
    except OSError as e:
        error_exit("could not write '{}': {}".format(html_path, e))
    return html_path

if __name__ == "__main__":
    template_file = check_file(sys.argv)
    settings = load_settings("settings.py")
    template = load_template(template_file)
    rendered_content = render(template, settings)
    html_file = write_html(template_file, rendered_content)
