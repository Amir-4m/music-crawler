import difflib

from django.utils.html import format_html

from .models import Prototype


def diff_strings():
    all_pro = Prototype.objects.all().iterator()
    for pro in all_pro:
        a = pro.string_one
        b = pro.String_two
        output = []
        matcher = difflib.SequenceMatcher(None, a, b)
        for opcode, a0, a1, b0, b1 in matcher.get_opcodes():
            if opcode == "equal":
                output.append(a[a0:a1])
            elif opcode == "insert":
                output.append(format_html('<span style="color: green;">{}</span>', b[b0:b1]))
            elif opcode == "delete":
                output.append(format_html('<span style="color: red;">{}</span>', a[a0:a1]))
            elif opcode == "replace":
                output.append(format_html('<span style="color: blue;">{}</span>', b[b0:b1]))
                output.append(format_html('<span style="color: orange;">{}</span>', a[a0:a1]))

        pro.difference = "".join(output)
        pro.save()
