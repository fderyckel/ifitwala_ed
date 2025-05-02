# Copyright (c) 2024, Francois de Ryckel  and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.website.website_generator import WebsiteGenerator
from frappe.utils.nestedset import NestedSet
from frappe import _dict

class Program(WebsiteGenerator):
    # which field becomes the slug in the URL
    website_generator = "program_slug"

    # generator settings: route prefix, template, publish flag, title field
    website = _dict(
        route="program",
        template="templates/generators/program.html",
        condition_field="is_published",
        page_title_field="program_name",
    )

    def validate(self):
        # your duplicate‐course guard
        self.validate_duplicate_course()
        # ensure route is recalculated on every save
        self.set_route()

    def validate_duplicate_course(self):
        seen = set()
        for row in self.courses:
            if row.course in seen:
                frappe.throw(_("Course {0} entered twice").format(row.course))
            seen.add(row.course)

    def get_context(self, context):
        # stop caching so edits appear immediately
        context.no_cache = True

        # page basics
        context.title = self.program_name
        context.program = self

        # breadcrumbs back to /programs
        crumbs = [{"name": "/programs", "title": "Programs"}]
        parent = self.parent_program
        while parent:
            p = frappe.get_doc("Program", parent)
            crumbs.append({
                "name": f"/program/{p.program_slug}",
                "title": p.program_name
            })
            parent = p.parent_program
        context.parents = crumbs

        # if this node is a group, list its children
        if self.is_group:
            context.children = [
                frappe.get_doc("Program", child.name)
                for child in self.get_children()
            ]

        return context
