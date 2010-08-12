# -*- coding: utf-8 -*-
from django import template
from django.conf import settings
from django.utils.encoding import smart_str, force_unicode
from django.utils.safestring import mark_safe

import os

register = template.Library()

@register.filter
def resume(value, arg):
    "Renvoie les permiers éléments de la liste dans une balise HTML (span par exemple) avec un title qui contient la liste complète"
    see_more = u"""<div dojoType="dijit.form.DropDownButton" class="bouton_discret">
        <span>...</span>
        <div dojoType="dijit.TooltipDialog" title="Liste complète" style="display:none;">
            %s
        </div>
    </div>""" % (" ".join([unicode(v) for v in value]),)

    dict = {
        "balise"    : arg,
        "complet"   : " ".join([unicode(v) for v in value]),
        "resume"    : "%s%s" % (" ".join([unicode(v) for v in value[:5]]), len(value) >= 5 and see_more or ""),
        }
    return mark_safe("""<%(balise)s>%(resume)s</%(balise)s>""" % dict)

@register.filter
def is_list(value):
    "Détermine si value est une liste"
    if isinstance(value, (list, tuple)):
        return True
    return False

@register.filter
def columnize(data, cols):
    rows = []
    row = []
    index = 0
    for object in data:
        row.append(object)
        index = index + 1
        if index % cols == 0:
            rows.append(row)
            row = []
    # Si il en reste :
    if len(row) > 0:
        row.extend([None for i in range(cols - len(row))])
        rows.append(row)
    return rows

@register.filter
def list_of_dict(data):
    if not data:
        return data
    if isinstance(data, (int, str, unicode)):
        return data
    headers = data[0].keys()
    html_thead = """
        <thead>
            <tr>
                %s
            </tr>
        </thead>""" % ("".join(["<th>%s</th>" % (header,) for header in headers]),)
    html_lines = []
    for dataline in data:
        html_lines.append("<tr>%s</tr>" % ("".join(["""<td>%s</td>""" % (dataline.get(header,None),) for header in headers]),))
    html_tbody = """
        <tbody>
            %s
        </tbody>
    """ % ("".join([html_line for html_line in html_lines]),)
    return mark_safe(html_thead + html_tbody)
