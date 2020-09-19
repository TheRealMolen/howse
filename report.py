from datetime import datetime


def gen_html(properties):
    html = """<!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <title>maybe howses</title>
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootswatch/4.5.2/lux/bootstrap.min.css">
    </head>
    <body>
        <div class="container">
            <div class="jumbotron">
                <h1 class="display-4">maybe howses by the sea</h1>
            </div>
    """

    for prop in properties:
        html += '<div class="row py-3 border-bottom border-warning">'
        html += ' <div class="col-4"><a href="%s" target="_blank"><img src="%s" style="max-width:354px"></a></div>' % (prop['url'],prop['thumb'])
        html += ' <div class="col-8">'
        html += '  <h3><a href="%s" target="_blank">%s</a></h3>' % (prop['url'], prop['description'])
        html += '  <h2>%s</h2>' % prop['price']
        html += '  <h5>%s</h5>' % prop['address'] if 'address' in prop else prop['details']['address']
        if 'rooms' in prop:
            html += '  <h5>%s</h5>' % prop['rooms']
        html += '  <h5 class="d-inline-block">max %sMbps</h5>' % (prop['details']['maxSpeed'] if 'maxSpeed' in prop['details'] else '<span class="p-1 bg-warning text-white">??</span>')
        
        firstlisted = datetime.strptime(prop['details']['firstlisted'], "%Y-%m-%dT%H:%M:%S")
        firstlisted = firstlisted.strftime('%b %Y')
        html += '  <h5 class="d-inline-block pl-4"><small>first listed </small>%s</h5>' % firstlisted
        html += '  <p>%s</p>' % prop['blurb']
        html += '  <small><small>%s</small></small>' % prop['id']
        html += ' </div>'
        html += '</div>'

    html += """
        </div>
        <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js" integrity="sha384-DfXdz2htPH0lsSSs5nCTpuj/zy4C+OGpamoFVy38MVBnE+IbbVYUew+OrCXaRkfj" crossorigin="anonymous"></script>
        <script src="https://cdn.jsdelivr.net/npm/popper.js@1.16.1/dist/umd/popper.min.js" integrity="sha384-9/reFTGAW83EW2RDu2S0VKaIzap3H66lZH81PoYlFhbGU+6BZp6G7niu735Sk7lN" crossorigin="anonymous"></script>
        <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js" integrity="sha384-B4gt1jrGC7Jh4AgTPSdUtOBvfO8shuf57BaghqFfPlYxofvL8/KUEfYiJOMMV+rV" crossorigin="anonymous"></script>
    </body>
    </html>"""

    return html
        

if __name__ == '__main__':
    import json
    properties = []
    with open('truro20mi_rmv.json') as infile:
        properties = json.load(infile)
    html = gen_html(properties)
    with open('maybe-howses-rmv.html', 'wt', encoding='utf-8') as outFile:
        outFile.write(html)