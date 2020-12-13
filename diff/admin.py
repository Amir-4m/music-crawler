import difflib

from django.contrib import admin

# Register your models here.
from django.http import HttpResponseRedirect
from django.utils.html import format_html

from diff.forms import Changes
from diff.models import Prototype

from django.shortcuts import render


@admin.register(Prototype)
class PrototypeAdmin(admin.ModelAdmin):
    list_display = ("id", "string_one",)
    change_form_template = "changes.html"

    def response_change(self, request, instance):
        form = None

        if "_changes" in request.POST:
            form = Changes(request.POST)
            if form.is_valid():
                instance_id = instance.id
                str_one = Prototype.objects.get(id=instance_id).string_one
                str_two = Prototype.objects.get(id=instance_id).String_two

                output = []

                matcher = difflib.SequenceMatcher(None, str_one, str_two)
                for opcode, a0, a1, b0, b1 in matcher.get_opcodes():
                    if opcode == "equal":
                        output.append(str_one[a0:a1])
                    elif opcode == "insert":
                        output.append(format_html('<span style="color: green;">{}</span>', str_two[b0:b1]))
                    elif opcode == "delete":
                        output.append(format_html('<span style="color: red;">{}</span>', str_one[a0:a1]))
                    elif opcode == "replace":
                        output.append(format_html('<span style="color: green;">{}</span>', str_two[b0:b1]))
                        output.append(format_html('<span style="color: red;">{}</span>', str_one[a0:a1]))

                instance.string_diff = "".join(output)
                added = ("".join(output)).count("green")
                deleted = ("".join(output)).count("red")
                instance.changes = f"word added = +{added}, word deleted = -{deleted}"
                instance.save()
                return HttpResponseRedirect(request.get_full_path())

            if not form:
                form = Changes(initial={'_selected_action': request.POST.getlist(admin.ACTION_CHECKBOX_NAME)})

            return render(request, 'changes_form.html', {'changes': form, 'instance': instance})
