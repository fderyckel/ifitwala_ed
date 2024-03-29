# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
import inspect

from frappe.utils import getdate

__version__ = '0.0.1'

def get_default_organization(user=None):
	'''Get default organization for user'''
	from frappe.defaults import get_user_default_as_list

	if not user:
		user = frappe.session.user

	organizations = get_user_default_as_list(user, 'organization')
	if organizations:
		default_organization = organizations[0]
	else:
		default_organization = frappe.db.get_single_value('Global Defaults', 'default_organization')

	return default_organization

def get_default_currency():
	'''Returns the currency of the default organization'''
	organization = get_default_organization()
	if organization:
		return frappe.get_cached_value('Organization',  organization,  'default_currency')

def get_default_cost_center(organization):
	'''Returns the default cost center of the organization'''
	if not organization:
		return None

	if not frappe.flags.organization_cost_center:
		frappe.flags.organization_cost_center = {}
	if not organization in frappe.flags.organization_cost_center:
		frappe.flags.organization_cost_center[organization] = frappe.get_cached_value('Organization',  organization,  'cost_center')
	return frappe.flags.organization_cost_center[organization]

def get_organization_currency(organization):
	'''Returns the default organization currency'''
	if not frappe.flags.organization_currency:
		frappe.flags.organization_currency = {}
	if not organization in frappe.flags.organization_currency:
		frappe.flags.organization_currency[organization] = frappe.db.get_value('Organization',  organization,  'default_currency', cache=True)
	return frappe.flags.organization_currency[organization]

def encode_organization_abbr(name, organization):
	'''Returns name encoded with organization abbreviation'''
	organization_abbr = frappe.get_cached_value('Organization',  organization,  "abbr")
	parts = name.rsplit(" - ", 1)

	if parts[-1].lower() != organization_abbr.lower():
		parts.append(organization_abbr)

	return " - ".join(parts)

def is_perpetual_inventory_enabled(organization):
	if not organization:
		organization = "_Test Organization" if frappe.flags.in_test else get_default_organization()

	if not hasattr(frappe.local, 'enable_perpetual_inventory'):
		frappe.local.enable_perpetual_inventory = {}

	if not organization in frappe.local.enable_perpetual_inventory:
		frappe.local.enable_perpetual_inventory[organization] = frappe.get_cached_value('Organization',
			organization,  "enable_perpetual_inventory") or 0

	return frappe.local.enable_perpetual_inventory[organization]

def get_default_finance_book(organization=None):
	if not organization:
		organization = get_default_organization()

	if not hasattr(frappe.local, 'default_finance_book'):
		frappe.local.default_finance_book = {}

	if not organization in frappe.local.default_finance_book:
		frappe.local.default_finance_book[organization] = frappe.get_cached_value('Organization',
			organization,  "default_finance_book")

	return frappe.local.default_finance_book[organization]

def get_party_account_type(party_type):
	if not hasattr(frappe.local, 'party_account_types'):
		frappe.local.party_account_types = {}

	if not party_type in frappe.local.party_account_types:
		frappe.local.party_account_types[party_type] = frappe.db.get_value("Party Type",
			party_type, "account_type") or ''

	return frappe.local.party_account_types[party_type]

def get_region(organization=None):
	'''Return the default country based on flag, organization or global settings
	You can also set global organization flag in `frappe.flags.organization`
	'''
	if organization or frappe.flags.organization:
		return frappe.get_cached_value('Organization', organization or frappe.flags.organization, 'country')
	elif frappe.flags.country:
		return frappe.flags.country
	else:
		return frappe.get_system_settings('country')

def allow_regional(fn):
	'''Decorator to make a function regionally overridable
	Example:
	@erpnext.allow_regional
	def myfunction():
	  pass'''
	def caller(*args, **kwargs):
		region = get_region()
		fn_name = inspect.getmodule(fn).__name__ + '.' + fn.__name__
		if region in regional_overrides and fn_name in regional_overrides[region]:
			return frappe.get_attr(regional_overrides[region][fn_name])(*args, **kwargs)
		else:
			return fn(*args, **kwargs)

	return
