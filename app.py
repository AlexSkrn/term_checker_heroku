#!/usr/bin/env python3
import os

from flask import Flask
from flask import render_template
from flask import request
from flask import redirect

from query_db import verify_terms


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY').encode()

ALLOWED_EXTENSIONS = {'txt'}


def allowed_file(filename):
    """Check if the file extension is okey."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def read_file(a_string):
    """Read bitext and return a list of tuples."""
    res = []
    for line in a_string.split('\n'):
        if len(line) > 0:
            try:
                src, trg = line.split('\t')
            except ValueError as err:
                print('ERROR when reading file:', err)
                print('Wrong line: ', line)
                pass
            else:
                res.append(
                       (src.strip(), trg.strip())
                       )
    return res


@app.route('/', methods=['GET', 'POST'])
def home():
    """."""
    if request.method == 'POST':
        # check if the post request has the expected parts
        if 'bitext' not in request.files \
           or 'glossary' not in request.files\
           or 'directions' not in request.form \
           or 'outcomes' not in request.form:
            return redirect(request.url)
        bitext_file = request.files['bitext']
        glossary_file = request.files['glossary']
        # if user does not select either of the files
        if bitext_file.filename == '' or glossary_file.filename == '':
            return redirect(request.url)
        if bitext_file and allowed_file(bitext_file.filename) \
           and glossary_file and allowed_file(glossary_file.filename):

            direction = request.form['directions']
            outcome = request.form['outcomes']

            bitext = read_file(bitext_file.read().decode('utf-8'))
            glossary = read_file(glossary_file.read().decode('utf-8'))

            title = 'Errors'
            successes = False
            if outcome == 'successes':
                title = 'Successes'
                successes = True
            data = verify_terms(direction,
                                bitext,
                                glossary,
                                successes=successes)
            if len(data) > 0:
                return render_template('results.jinja2', title=title,
                                       results=data)
            else:
                return render_template('results.jinja2', title=title,
                                       no_res="- No results to display")
    return render_template('home.jinja2')


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 6738))
    app.run(host='0.0.0.0', port=port, debug=True)  # REMOVE debug=True
