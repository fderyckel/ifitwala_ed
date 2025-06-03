(() => {
  // ../ifitwala_ed/ifitwala_ed/public/js/utils.js
  frappe.provide("ifitwala_ed.utils");
  $.extend(ifitwala_ed.utils, {
    get_tree_options: function(option) {
      let unscrub_option = frappe.model.unscrub(option);
      let user_permission = frappe.defaults.get_user_permissions();
      let options;
      if (user_permission && user_permission[unscrub_option]) {
        options = user_permission[unscrub_option].map((perm) => perm.doc);
      } else {
        options = $.map(locals[`:${unscrub_option}`], function(c3) {
          return c3.name;
        }).sort();
      }
      return options.filter((value, index4, self) => self.indexOf(value) === index4);
    },
    get_tree_default: function(option) {
      let options = this.get_tree_options(option);
      if (options.includes(frappe.defaults.get_default(option))) {
        return frappe.defaults.get_default(option);
      } else {
        return options[0];
      }
    }
  });
  frappe.form.link_formatters["Employee"] = function(value, doc, df) {
    return add_link_title(value, doc, df, "employee_full_name");
  };
  function add_link_title(value, doc, df, title_field) {
    if (doc && value && doc[title_field] && doc[title_field] !== value && doc[df.fieldname] === value) {
      return value + ": " + doc[title_field];
    } else if (!value && doc.doctype && doc[title_field]) {
      return doc[title_field];
    } else {
      return value;
    }
  }

  // ../ifitwala_ed/ifitwala_ed/public/js/queries.js
  frappe.provide("ifitwala_ed.queries");
  $.extend(ifitwala_ed.queries, {
    user: function() {
      return { query: "frappe.core.doctype.user.user.user_query" };
    },
    contact_query: function(doc) {
      if (frappe.dynamic_link) {
        if (!doc[frappe.dynamic_link.fieldname]) {
          cur_frm.scroll_to_field(frappe.dynamic_link.fieldname);
          frappe.show_alert({
            message: __("Please set {0} first.", [
              __(frappe.meta.get_label(doc.doctype, frappe.dynamic_link.fieldname, doc.name))
            ]),
            indicator: "orange"
          });
        }
        return {
          query: "frappe.contacts.doctype.contact.contact.contact_query",
          filters: {
            link_doctype: frappe.dynamic_link.doctype,
            link_name: doc[frappe.dynamic_link.fieldname]
          }
        };
      }
    },
    organization_contact_query: function(doc) {
      if (!doc.organization) {
        frappe.throw(__("Please set {0}", [__(frappe.meta.get_label(doc.doctype, "organization", doc.name))]));
      }
      return {
        query: "frappe.contacts.doctype.contact.contact.contact_query",
        filters: { link_doctype: "Organization", link_name: doc.organization }
      };
    },
    address_query: function(doc) {
      if (frappe.dynamic_link) {
        if (!doc[frappe.dynamic_link.fieldname]) {
          cur_frm.scroll_to_field(frappe.dynamic_link.fieldname);
          frappe.show_alert({
            message: __("Please set {0} first.", [
              __(frappe.meta.get_label(doc.doctype, frappe.dynamic_link.fieldname, doc.name))
            ]),
            indicator: "orange"
          });
        }
        return {
          query: "frappe.contacts.doctype.address.address.address_query",
          filters: {
            link_doctype: frappe.dynamic_link.doctype,
            link_name: doc[frappe.dynamic_link.fieldname]
          }
        };
      }
    },
    organization_address_query: function(doc) {
      if (!doc.organization) {
        cur_frm.scroll_to_field("organization");
        frappe.show_alert({
          message: __("Please set {0} first.", [
            __(frappe.meta.get_label(doc.doctype, "organization", doc.name))
          ]),
          indicator: "orange"
        });
      }
      return {
        query: "frappe.contacts.doctype.address.address.address_query",
        filters: { link_doctype: "Organization", link_name: doc.organization }
      };
    },
    not_a_group_filter: function() {
      return { filters: { is_group: 0 } };
    },
    employee: function() {
      return { query: "ifitwala_ed.controllers.queries.employee_query" };
    },
    location: function(doc) {
      return {
        filters: [
          ["Location", "organization", "in", ["", cstr(doc.organization)]],
          ["Location", "is_group", "=", 0]
        ]
      };
    }
  });
  ifitwala_ed.queries.setup_queries = function(frm, options, query_fn) {
    var me = this;
    var set_query = function(doctype, parentfield) {
      var link_fields = frappe.meta.get_docfields(doctype, frm.doc.name, {
        fieldtype: "Link",
        options
      });
      $.each(link_fields, function(i3, df) {
        if (parentfield) {
          frm.set_query(df.fieldname, parentfield, query_fn);
        } else {
          frm.set_query(df.fieldname, query_fn);
        }
      });
    };
    set_query(frm.doc.doctype);
    $.each(
      frappe.meta.get_docfields(frm.doc.doctype, frm.doc.name, { fieldtype: "Table" }),
      function(i3, df) {
        set_query(df.options, df.fieldname);
      }
    );
  };

  // ../ifitwala_ed/node_modules/preact/dist/preact.module.js
  var n;
  var l;
  var u;
  var i;
  var t;
  var r;
  var o;
  var f;
  var e;
  var c = {};
  var s = [];
  var a = /acit|ex(?:s|g|n|p|$)|rph|grid|ows|mnc|ntw|ine[ch]|zoo|^ord|itera/i;
  function h(n2, l3) {
    for (var u3 in l3)
      n2[u3] = l3[u3];
    return n2;
  }
  function v(n2) {
    var l3 = n2.parentNode;
    l3 && l3.removeChild(n2);
  }
  function y(l3, u3, i3) {
    var t3, r3, o2, f3 = {};
    for (o2 in u3)
      "key" == o2 ? t3 = u3[o2] : "ref" == o2 ? r3 = u3[o2] : f3[o2] = u3[o2];
    if (arguments.length > 2 && (f3.children = arguments.length > 3 ? n.call(arguments, 2) : i3), "function" == typeof l3 && null != l3.defaultProps)
      for (o2 in l3.defaultProps)
        void 0 === f3[o2] && (f3[o2] = l3.defaultProps[o2]);
    return p(l3, f3, t3, r3, null);
  }
  function p(n2, i3, t3, r3, o2) {
    var f3 = { type: n2, props: i3, key: t3, ref: r3, __k: null, __: null, __b: 0, __e: null, __d: void 0, __c: null, __h: null, constructor: void 0, __v: null == o2 ? ++u : o2 };
    return null == o2 && null != l.vnode && l.vnode(f3), f3;
  }
  function d() {
    return { current: null };
  }
  function _(n2) {
    return n2.children;
  }
  function k(n2, l3, u3, i3, t3) {
    var r3;
    for (r3 in u3)
      "children" === r3 || "key" === r3 || r3 in l3 || g(n2, r3, null, u3[r3], i3);
    for (r3 in l3)
      t3 && "function" != typeof l3[r3] || "children" === r3 || "key" === r3 || "value" === r3 || "checked" === r3 || u3[r3] === l3[r3] || g(n2, r3, l3[r3], u3[r3], i3);
  }
  function b(n2, l3, u3) {
    "-" === l3[0] ? n2.setProperty(l3, null == u3 ? "" : u3) : n2[l3] = null == u3 ? "" : "number" != typeof u3 || a.test(l3) ? u3 : u3 + "px";
  }
  function g(n2, l3, u3, i3, t3) {
    var r3;
    n:
      if ("style" === l3)
        if ("string" == typeof u3)
          n2.style.cssText = u3;
        else {
          if ("string" == typeof i3 && (n2.style.cssText = i3 = ""), i3)
            for (l3 in i3)
              u3 && l3 in u3 || b(n2.style, l3, "");
          if (u3)
            for (l3 in u3)
              i3 && u3[l3] === i3[l3] || b(n2.style, l3, u3[l3]);
        }
      else if ("o" === l3[0] && "n" === l3[1])
        r3 = l3 !== (l3 = l3.replace(/Capture$/, "")), l3 = l3.toLowerCase() in n2 ? l3.toLowerCase().slice(2) : l3.slice(2), n2.l || (n2.l = {}), n2.l[l3 + r3] = u3, u3 ? i3 || n2.addEventListener(l3, r3 ? w : m, r3) : n2.removeEventListener(l3, r3 ? w : m, r3);
      else if ("dangerouslySetInnerHTML" !== l3) {
        if (t3)
          l3 = l3.replace(/xlink(H|:h)/, "h").replace(/sName$/, "s");
        else if ("width" !== l3 && "height" !== l3 && "href" !== l3 && "list" !== l3 && "form" !== l3 && "tabIndex" !== l3 && "download" !== l3 && l3 in n2)
          try {
            n2[l3] = null == u3 ? "" : u3;
            break n;
          } catch (n3) {
          }
        "function" == typeof u3 || (null == u3 || false === u3 && -1 == l3.indexOf("-") ? n2.removeAttribute(l3) : n2.setAttribute(l3, u3));
      }
  }
  function m(n2) {
    t = true;
    try {
      return this.l[n2.type + false](l.event ? l.event(n2) : n2);
    } finally {
      t = false;
    }
  }
  function w(n2) {
    t = true;
    try {
      return this.l[n2.type + true](l.event ? l.event(n2) : n2);
    } finally {
      t = false;
    }
  }
  function x(n2, l3) {
    this.props = n2, this.context = l3;
  }
  function A(n2, l3) {
    if (null == l3)
      return n2.__ ? A(n2.__, n2.__.__k.indexOf(n2) + 1) : null;
    for (var u3; l3 < n2.__k.length; l3++)
      if (null != (u3 = n2.__k[l3]) && null != u3.__e)
        return u3.__e;
    return "function" == typeof n2.type ? A(n2) : null;
  }
  function P(n2) {
    var l3, u3;
    if (null != (n2 = n2.__) && null != n2.__c) {
      for (n2.__e = n2.__c.base = null, l3 = 0; l3 < n2.__k.length; l3++)
        if (null != (u3 = n2.__k[l3]) && null != u3.__e) {
          n2.__e = n2.__c.base = u3.__e;
          break;
        }
      return P(n2);
    }
  }
  function C(n2) {
    t ? setTimeout(n2) : f(n2);
  }
  function T(n2) {
    (!n2.__d && (n2.__d = true) && r.push(n2) && !$2.__r++ || o !== l.debounceRendering) && ((o = l.debounceRendering) || C)($2);
  }
  function $2() {
    var n2, l3, u3, i3, t3, o2, f3, e3;
    for (r.sort(function(n3, l4) {
      return n3.__v.__b - l4.__v.__b;
    }); n2 = r.shift(); )
      n2.__d && (l3 = r.length, i3 = void 0, t3 = void 0, f3 = (o2 = (u3 = n2).__v).__e, (e3 = u3.__P) && (i3 = [], (t3 = h({}, o2)).__v = o2.__v + 1, M(e3, o2, t3, u3.__n, void 0 !== e3.ownerSVGElement, null != o2.__h ? [f3] : null, i3, null == f3 ? A(o2) : f3, o2.__h), N(i3, o2), o2.__e != f3 && P(o2)), r.length > l3 && r.sort(function(n3, l4) {
        return n3.__v.__b - l4.__v.__b;
      }));
    $2.__r = 0;
  }
  function H(n2, l3, u3, i3, t3, r3, o2, f3, e3, a3) {
    var h3, v3, y3, d2, k3, b3, g4, m3 = i3 && i3.__k || s, w4 = m3.length;
    for (u3.__k = [], h3 = 0; h3 < l3.length; h3++)
      if (null != (d2 = u3.__k[h3] = null == (d2 = l3[h3]) || "boolean" == typeof d2 ? null : "string" == typeof d2 || "number" == typeof d2 || "bigint" == typeof d2 ? p(null, d2, null, null, d2) : Array.isArray(d2) ? p(_, { children: d2 }, null, null, null) : d2.__b > 0 ? p(d2.type, d2.props, d2.key, d2.ref ? d2.ref : null, d2.__v) : d2)) {
        if (d2.__ = u3, d2.__b = u3.__b + 1, null === (y3 = m3[h3]) || y3 && d2.key == y3.key && d2.type === y3.type)
          m3[h3] = void 0;
        else
          for (v3 = 0; v3 < w4; v3++) {
            if ((y3 = m3[v3]) && d2.key == y3.key && d2.type === y3.type) {
              m3[v3] = void 0;
              break;
            }
            y3 = null;
          }
        M(n2, d2, y3 = y3 || c, t3, r3, o2, f3, e3, a3), k3 = d2.__e, (v3 = d2.ref) && y3.ref != v3 && (g4 || (g4 = []), y3.ref && g4.push(y3.ref, null, d2), g4.push(v3, d2.__c || k3, d2)), null != k3 ? (null == b3 && (b3 = k3), "function" == typeof d2.type && d2.__k === y3.__k ? d2.__d = e3 = I(d2, e3, n2) : e3 = z(n2, d2, y3, m3, k3, e3), "function" == typeof u3.type && (u3.__d = e3)) : e3 && y3.__e == e3 && e3.parentNode != n2 && (e3 = A(y3));
      }
    for (u3.__e = b3, h3 = w4; h3--; )
      null != m3[h3] && ("function" == typeof u3.type && null != m3[h3].__e && m3[h3].__e == u3.__d && (u3.__d = L(i3).nextSibling), q(m3[h3], m3[h3]));
    if (g4)
      for (h3 = 0; h3 < g4.length; h3++)
        S(g4[h3], g4[++h3], g4[++h3]);
  }
  function I(n2, l3, u3) {
    for (var i3, t3 = n2.__k, r3 = 0; t3 && r3 < t3.length; r3++)
      (i3 = t3[r3]) && (i3.__ = n2, l3 = "function" == typeof i3.type ? I(i3, l3, u3) : z(u3, i3, i3, t3, i3.__e, l3));
    return l3;
  }
  function j(n2, l3) {
    return l3 = l3 || [], null == n2 || "boolean" == typeof n2 || (Array.isArray(n2) ? n2.some(function(n3) {
      j(n3, l3);
    }) : l3.push(n2)), l3;
  }
  function z(n2, l3, u3, i3, t3, r3) {
    var o2, f3, e3;
    if (void 0 !== l3.__d)
      o2 = l3.__d, l3.__d = void 0;
    else if (null == u3 || t3 != r3 || null == t3.parentNode)
      n:
        if (null == r3 || r3.parentNode !== n2)
          n2.appendChild(t3), o2 = null;
        else {
          for (f3 = r3, e3 = 0; (f3 = f3.nextSibling) && e3 < i3.length; e3 += 1)
            if (f3 == t3)
              break n;
          n2.insertBefore(t3, r3), o2 = r3;
        }
    return void 0 !== o2 ? o2 : t3.nextSibling;
  }
  function L(n2) {
    var l3, u3, i3;
    if (null == n2.type || "string" == typeof n2.type)
      return n2.__e;
    if (n2.__k) {
      for (l3 = n2.__k.length - 1; l3 >= 0; l3--)
        if ((u3 = n2.__k[l3]) && (i3 = L(u3)))
          return i3;
    }
    return null;
  }
  function M(n2, u3, i3, t3, r3, o2, f3, e3, c3) {
    var s3, a3, v3, y3, p3, d2, k3, b3, g4, m3, w4, A3, P3, C3, T4, $4 = u3.type;
    if (void 0 !== u3.constructor)
      return null;
    null != i3.__h && (c3 = i3.__h, e3 = u3.__e = i3.__e, u3.__h = null, o2 = [e3]), (s3 = l.__b) && s3(u3);
    try {
      n:
        if ("function" == typeof $4) {
          if (b3 = u3.props, g4 = (s3 = $4.contextType) && t3[s3.__c], m3 = s3 ? g4 ? g4.props.value : s3.__ : t3, i3.__c ? k3 = (a3 = u3.__c = i3.__c).__ = a3.__E : ("prototype" in $4 && $4.prototype.render ? u3.__c = a3 = new $4(b3, m3) : (u3.__c = a3 = new x(b3, m3), a3.constructor = $4, a3.render = B), g4 && g4.sub(a3), a3.props = b3, a3.state || (a3.state = {}), a3.context = m3, a3.__n = t3, v3 = a3.__d = true, a3.__h = [], a3._sb = []), null == a3.__s && (a3.__s = a3.state), null != $4.getDerivedStateFromProps && (a3.__s == a3.state && (a3.__s = h({}, a3.__s)), h(a3.__s, $4.getDerivedStateFromProps(b3, a3.__s))), y3 = a3.props, p3 = a3.state, a3.__v = u3, v3)
            null == $4.getDerivedStateFromProps && null != a3.componentWillMount && a3.componentWillMount(), null != a3.componentDidMount && a3.__h.push(a3.componentDidMount);
          else {
            if (null == $4.getDerivedStateFromProps && b3 !== y3 && null != a3.componentWillReceiveProps && a3.componentWillReceiveProps(b3, m3), !a3.__e && null != a3.shouldComponentUpdate && false === a3.shouldComponentUpdate(b3, a3.__s, m3) || u3.__v === i3.__v) {
              for (u3.__v !== i3.__v && (a3.props = b3, a3.state = a3.__s, a3.__d = false), u3.__e = i3.__e, u3.__k = i3.__k, u3.__k.forEach(function(n3) {
                n3 && (n3.__ = u3);
              }), w4 = 0; w4 < a3._sb.length; w4++)
                a3.__h.push(a3._sb[w4]);
              a3._sb = [], a3.__h.length && f3.push(a3);
              break n;
            }
            null != a3.componentWillUpdate && a3.componentWillUpdate(b3, a3.__s, m3), null != a3.componentDidUpdate && a3.__h.push(function() {
              a3.componentDidUpdate(y3, p3, d2);
            });
          }
          if (a3.context = m3, a3.props = b3, a3.__P = n2, A3 = l.__r, P3 = 0, "prototype" in $4 && $4.prototype.render) {
            for (a3.state = a3.__s, a3.__d = false, A3 && A3(u3), s3 = a3.render(a3.props, a3.state, a3.context), C3 = 0; C3 < a3._sb.length; C3++)
              a3.__h.push(a3._sb[C3]);
            a3._sb = [];
          } else
            do {
              a3.__d = false, A3 && A3(u3), s3 = a3.render(a3.props, a3.state, a3.context), a3.state = a3.__s;
            } while (a3.__d && ++P3 < 25);
          a3.state = a3.__s, null != a3.getChildContext && (t3 = h(h({}, t3), a3.getChildContext())), v3 || null == a3.getSnapshotBeforeUpdate || (d2 = a3.getSnapshotBeforeUpdate(y3, p3)), T4 = null != s3 && s3.type === _ && null == s3.key ? s3.props.children : s3, H(n2, Array.isArray(T4) ? T4 : [T4], u3, i3, t3, r3, o2, f3, e3, c3), a3.base = u3.__e, u3.__h = null, a3.__h.length && f3.push(a3), k3 && (a3.__E = a3.__ = null), a3.__e = false;
        } else
          null == o2 && u3.__v === i3.__v ? (u3.__k = i3.__k, u3.__e = i3.__e) : u3.__e = O(i3.__e, u3, i3, t3, r3, o2, f3, c3);
      (s3 = l.diffed) && s3(u3);
    } catch (n3) {
      u3.__v = null, (c3 || null != o2) && (u3.__e = e3, u3.__h = !!c3, o2[o2.indexOf(e3)] = null), l.__e(n3, u3, i3);
    }
  }
  function N(n2, u3) {
    l.__c && l.__c(u3, n2), n2.some(function(u4) {
      try {
        n2 = u4.__h, u4.__h = [], n2.some(function(n3) {
          n3.call(u4);
        });
      } catch (n3) {
        l.__e(n3, u4.__v);
      }
    });
  }
  function O(l3, u3, i3, t3, r3, o2, f3, e3) {
    var s3, a3, h3, y3 = i3.props, p3 = u3.props, d2 = u3.type, _3 = 0;
    if ("svg" === d2 && (r3 = true), null != o2) {
      for (; _3 < o2.length; _3++)
        if ((s3 = o2[_3]) && "setAttribute" in s3 == !!d2 && (d2 ? s3.localName === d2 : 3 === s3.nodeType)) {
          l3 = s3, o2[_3] = null;
          break;
        }
    }
    if (null == l3) {
      if (null === d2)
        return document.createTextNode(p3);
      l3 = r3 ? document.createElementNS("http://www.w3.org/2000/svg", d2) : document.createElement(d2, p3.is && p3), o2 = null, e3 = false;
    }
    if (null === d2)
      y3 === p3 || e3 && l3.data === p3 || (l3.data = p3);
    else {
      if (o2 = o2 && n.call(l3.childNodes), a3 = (y3 = i3.props || c).dangerouslySetInnerHTML, h3 = p3.dangerouslySetInnerHTML, !e3) {
        if (null != o2)
          for (y3 = {}, _3 = 0; _3 < l3.attributes.length; _3++)
            y3[l3.attributes[_3].name] = l3.attributes[_3].value;
        (h3 || a3) && (h3 && (a3 && h3.__html == a3.__html || h3.__html === l3.innerHTML) || (l3.innerHTML = h3 && h3.__html || ""));
      }
      if (k(l3, p3, y3, r3, e3), h3)
        u3.__k = [];
      else if (_3 = u3.props.children, H(l3, Array.isArray(_3) ? _3 : [_3], u3, i3, t3, r3 && "foreignObject" !== d2, o2, f3, o2 ? o2[0] : i3.__k && A(i3, 0), e3), null != o2)
        for (_3 = o2.length; _3--; )
          null != o2[_3] && v(o2[_3]);
      e3 || ("value" in p3 && void 0 !== (_3 = p3.value) && (_3 !== l3.value || "progress" === d2 && !_3 || "option" === d2 && _3 !== y3.value) && g(l3, "value", _3, y3.value, false), "checked" in p3 && void 0 !== (_3 = p3.checked) && _3 !== l3.checked && g(l3, "checked", _3, y3.checked, false));
    }
    return l3;
  }
  function S(n2, u3, i3) {
    try {
      "function" == typeof n2 ? n2(u3) : n2.current = u3;
    } catch (n3) {
      l.__e(n3, i3);
    }
  }
  function q(n2, u3, i3) {
    var t3, r3;
    if (l.unmount && l.unmount(n2), (t3 = n2.ref) && (t3.current && t3.current !== n2.__e || S(t3, null, u3)), null != (t3 = n2.__c)) {
      if (t3.componentWillUnmount)
        try {
          t3.componentWillUnmount();
        } catch (n3) {
          l.__e(n3, u3);
        }
      t3.base = t3.__P = null, n2.__c = void 0;
    }
    if (t3 = n2.__k)
      for (r3 = 0; r3 < t3.length; r3++)
        t3[r3] && q(t3[r3], u3, i3 || "function" != typeof n2.type);
    i3 || null == n2.__e || v(n2.__e), n2.__ = n2.__e = n2.__d = void 0;
  }
  function B(n2, l3, u3) {
    return this.constructor(n2, u3);
  }
  function D(u3, i3, t3) {
    var r3, o2, f3;
    l.__ && l.__(u3, i3), o2 = (r3 = "function" == typeof t3) ? null : t3 && t3.__k || i3.__k, f3 = [], M(i3, u3 = (!r3 && t3 || i3).__k = y(_, null, [u3]), o2 || c, c, void 0 !== i3.ownerSVGElement, !r3 && t3 ? [t3] : o2 ? null : i3.firstChild ? n.call(i3.childNodes) : null, f3, !r3 && t3 ? t3 : o2 ? o2.__e : i3.firstChild, r3), N(f3, u3);
  }
  function G(n2, l3) {
    var u3 = { __c: l3 = "__cC" + e++, __: n2, Consumer: function(n3, l4) {
      return n3.children(l4);
    }, Provider: function(n3) {
      var u4, i3;
      return this.getChildContext || (u4 = [], (i3 = {})[l3] = this, this.getChildContext = function() {
        return i3;
      }, this.shouldComponentUpdate = function(n4) {
        this.props.value !== n4.value && u4.some(function(n5) {
          n5.__e = true, T(n5);
        });
      }, this.sub = function(n4) {
        u4.push(n4);
        var l4 = n4.componentWillUnmount;
        n4.componentWillUnmount = function() {
          u4.splice(u4.indexOf(n4), 1), l4 && l4.call(n4);
        };
      }), n3.children;
    } };
    return u3.Provider.__ = u3.Consumer.contextType = u3;
  }
  n = s.slice, l = { __e: function(n2, l3, u3, i3) {
    for (var t3, r3, o2; l3 = l3.__; )
      if ((t3 = l3.__c) && !t3.__)
        try {
          if ((r3 = t3.constructor) && null != r3.getDerivedStateFromError && (t3.setState(r3.getDerivedStateFromError(n2)), o2 = t3.__d), null != t3.componentDidCatch && (t3.componentDidCatch(n2, i3 || {}), o2 = t3.__d), o2)
            return t3.__E = t3;
        } catch (l4) {
          n2 = l4;
        }
    throw n2;
  } }, u = 0, i = function(n2) {
    return null != n2 && void 0 === n2.constructor;
  }, t = false, x.prototype.setState = function(n2, l3) {
    var u3;
    u3 = null != this.__s && this.__s !== this.state ? this.__s : this.__s = h({}, this.state), "function" == typeof n2 && (n2 = n2(h({}, u3), this.props)), n2 && h(u3, n2), null != n2 && this.__v && (l3 && this._sb.push(l3), T(this));
  }, x.prototype.forceUpdate = function(n2) {
    this.__v && (this.__e = true, n2 && this.__h.push(n2), T(this));
  }, x.prototype.render = _, r = [], f = "function" == typeof Promise ? Promise.prototype.then.bind(Promise.resolve()) : setTimeout, $2.__r = 0, e = 0;

  // ../ifitwala_ed/node_modules/preact/hooks/dist/hooks.module.js
  var t2;
  var r2;
  var u2;
  var i2;
  var f2 = [];
  var c2 = [];
  var e2 = l.__b;
  var a2 = l.__r;
  var v2 = l.diffed;
  var l2 = l.__c;
  var m2 = l.unmount;
  function b2() {
    for (var t3; t3 = f2.shift(); )
      if (t3.__P && t3.__H)
        try {
          t3.__H.__h.forEach(k2), t3.__H.__h.forEach(w2), t3.__H.__h = [];
        } catch (r3) {
          t3.__H.__h = [], l.__e(r3, t3.__v);
        }
  }
  l.__b = function(n2) {
    r2 = null, e2 && e2(n2);
  }, l.__r = function(n2) {
    a2 && a2(n2), t2 = 0;
    var i3 = (r2 = n2.__c).__H;
    i3 && (u2 === r2 ? (i3.__h = [], r2.__h = [], i3.__.forEach(function(n3) {
      n3.__N && (n3.__ = n3.__N), n3.__V = c2, n3.__N = n3.i = void 0;
    })) : (i3.__h.forEach(k2), i3.__h.forEach(w2), i3.__h = [])), u2 = r2;
  }, l.diffed = function(t3) {
    v2 && v2(t3);
    var o2 = t3.__c;
    o2 && o2.__H && (o2.__H.__h.length && (1 !== f2.push(o2) && i2 === l.requestAnimationFrame || ((i2 = l.requestAnimationFrame) || j2)(b2)), o2.__H.__.forEach(function(n2) {
      n2.i && (n2.__H = n2.i), n2.__V !== c2 && (n2.__ = n2.__V), n2.i = void 0, n2.__V = c2;
    })), u2 = r2 = null;
  }, l.__c = function(t3, r3) {
    r3.some(function(t4) {
      try {
        t4.__h.forEach(k2), t4.__h = t4.__h.filter(function(n2) {
          return !n2.__ || w2(n2);
        });
      } catch (u3) {
        r3.some(function(n2) {
          n2.__h && (n2.__h = []);
        }), r3 = [], l.__e(u3, t4.__v);
      }
    }), l2 && l2(t3, r3);
  }, l.unmount = function(t3) {
    m2 && m2(t3);
    var r3, u3 = t3.__c;
    u3 && u3.__H && (u3.__H.__.forEach(function(n2) {
      try {
        k2(n2);
      } catch (n3) {
        r3 = n3;
      }
    }), u3.__H = void 0, r3 && l.__e(r3, u3.__v));
  };
  var g2 = "function" == typeof requestAnimationFrame;
  function j2(n2) {
    var t3, r3 = function() {
      clearTimeout(u3), g2 && cancelAnimationFrame(t3), setTimeout(n2);
    }, u3 = setTimeout(r3, 100);
    g2 && (t3 = requestAnimationFrame(r3));
  }
  function k2(n2) {
    var t3 = r2, u3 = n2.__c;
    "function" == typeof u3 && (n2.__c = void 0, u3()), r2 = t3;
  }
  function w2(n2) {
    var t3 = r2;
    n2.__c = n2.__(), r2 = t3;
  }

  // ../ifitwala_ed/node_modules/preact/compat/dist/compat.module.js
  function g3(n2, t3) {
    for (var e3 in t3)
      n2[e3] = t3[e3];
    return n2;
  }
  function C2(n2, t3) {
    for (var e3 in n2)
      if ("__source" !== e3 && !(e3 in t3))
        return true;
    for (var r3 in t3)
      if ("__source" !== r3 && n2[r3] !== t3[r3])
        return true;
    return false;
  }
  function w3(n2) {
    this.props = n2;
  }
  (w3.prototype = new x()).isPureReactComponent = true, w3.prototype.shouldComponentUpdate = function(n2, t3) {
    return C2(this.props, n2) || C2(this.state, t3);
  };
  var x3 = l.__b;
  l.__b = function(n2) {
    n2.type && n2.type.__f && n2.ref && (n2.props.ref = n2.ref, n2.ref = null), x3 && x3(n2);
  };
  var N2 = "undefined" != typeof Symbol && Symbol.for && Symbol.for("react.forward_ref") || 3911;
  var T3 = l.__e;
  l.__e = function(n2, t3, e3, r3) {
    if (n2.then) {
      for (var u3, o2 = t3; o2 = o2.__; )
        if ((u3 = o2.__c) && u3.__c)
          return null == t3.__e && (t3.__e = e3.__e, t3.__k = e3.__k), u3.__c(n2, t3);
    }
    T3(n2, t3, e3, r3);
  };
  var I2 = l.unmount;
  function L2(n2, t3, e3) {
    return n2 && (n2.__c && n2.__c.__H && (n2.__c.__H.__.forEach(function(n3) {
      "function" == typeof n3.__c && n3.__c();
    }), n2.__c.__H = null), null != (n2 = g3({}, n2)).__c && (n2.__c.__P === e3 && (n2.__c.__P = t3), n2.__c = null), n2.__k = n2.__k && n2.__k.map(function(n3) {
      return L2(n3, t3, e3);
    })), n2;
  }
  function U(n2, t3, e3) {
    return n2 && (n2.__v = null, n2.__k = n2.__k && n2.__k.map(function(n3) {
      return U(n3, t3, e3);
    }), n2.__c && n2.__c.__P === t3 && (n2.__e && e3.insertBefore(n2.__e, n2.__d), n2.__c.__e = true, n2.__c.__P = e3)), n2;
  }
  function D2() {
    this.__u = 0, this.t = null, this.__b = null;
  }
  function F3(n2) {
    var t3 = n2.__.__c;
    return t3 && t3.__a && t3.__a(n2);
  }
  function V2() {
    this.u = null, this.o = null;
  }
  l.unmount = function(n2) {
    var t3 = n2.__c;
    t3 && t3.__R && t3.__R(), t3 && true === n2.__h && (n2.type = null), I2 && I2(n2);
  }, (D2.prototype = new x()).__c = function(n2, t3) {
    var e3 = t3.__c, r3 = this;
    null == r3.t && (r3.t = []), r3.t.push(e3);
    var u3 = F3(r3.__v), o2 = false, i3 = function() {
      o2 || (o2 = true, e3.__R = null, u3 ? u3(l3) : l3());
    };
    e3.__R = i3;
    var l3 = function() {
      if (!--r3.__u) {
        if (r3.state.__a) {
          var n3 = r3.state.__a;
          r3.__v.__k[0] = U(n3, n3.__c.__P, n3.__c.__O);
        }
        var t4;
        for (r3.setState({ __a: r3.__b = null }); t4 = r3.t.pop(); )
          t4.forceUpdate();
      }
    }, c3 = true === t3.__h;
    r3.__u++ || c3 || r3.setState({ __a: r3.__b = r3.__v.__k[0] }), n2.then(i3, i3);
  }, D2.prototype.componentWillUnmount = function() {
    this.t = [];
  }, D2.prototype.render = function(n2, e3) {
    if (this.__b) {
      if (this.__v.__k) {
        var r3 = document.createElement("div"), o2 = this.__v.__k[0].__c;
        this.__v.__k[0] = L2(this.__b, r3, o2.__O = o2.__P);
      }
      this.__b = null;
    }
    var i3 = e3.__a && y(_, null, n2.fallback);
    return i3 && (i3.__h = null), [y(_, null, e3.__a ? null : n2.children), i3];
  };
  var W = function(n2, t3, e3) {
    if (++e3[1] === e3[0] && n2.o.delete(t3), n2.props.revealOrder && ("t" !== n2.props.revealOrder[0] || !n2.o.size))
      for (e3 = n2.u; e3; ) {
        for (; e3.length > 3; )
          e3.pop()();
        if (e3[1] < e3[0])
          break;
        n2.u = e3 = e3[2];
      }
  };
  function P2(n2) {
    return this.getChildContext = function() {
      return n2.context;
    }, n2.children;
  }
  function $3(n2) {
    var e3 = this, r3 = n2.i;
    e3.componentWillUnmount = function() {
      D(null, e3.l), e3.l = null, e3.i = null;
    }, e3.i && e3.i !== r3 && e3.componentWillUnmount(), n2.__v ? (e3.l || (e3.i = r3, e3.l = { nodeType: 1, parentNode: r3, childNodes: [], appendChild: function(n3) {
      this.childNodes.push(n3), e3.i.appendChild(n3);
    }, insertBefore: function(n3, t3) {
      this.childNodes.push(n3), e3.i.appendChild(n3);
    }, removeChild: function(n3) {
      this.childNodes.splice(this.childNodes.indexOf(n3) >>> 1, 1), e3.i.removeChild(n3);
    } }), D(y(P2, { context: e3.context }, n2.__v), e3.l)) : e3.l && e3.componentWillUnmount();
  }
  function j3(n2, e3) {
    var r3 = y($3, { __v: n2, i: e3 });
    return r3.containerInfo = e3, r3;
  }
  (V2.prototype = new x()).__a = function(n2) {
    var t3 = this, e3 = F3(t3.__v), r3 = t3.o.get(n2);
    return r3[0]++, function(u3) {
      var o2 = function() {
        t3.props.revealOrder ? (r3.push(u3), W(t3, n2, r3)) : u3();
      };
      e3 ? e3(o2) : o2();
    };
  }, V2.prototype.render = function(n2) {
    this.u = null, this.o = /* @__PURE__ */ new Map();
    var t3 = j(n2.children);
    n2.revealOrder && "b" === n2.revealOrder[0] && t3.reverse();
    for (var e3 = t3.length; e3--; )
      this.o.set(t3[e3], this.u = [1, 0, this.u]);
    return n2.children;
  }, V2.prototype.componentDidUpdate = V2.prototype.componentDidMount = function() {
    var n2 = this;
    this.o.forEach(function(t3, e3) {
      W(n2, e3, t3);
    });
  };
  var z2 = "undefined" != typeof Symbol && Symbol.for && Symbol.for("react.element") || 60103;
  var B2 = /^(?:accent|alignment|arabic|baseline|cap|clip(?!PathU)|color|dominant|fill|flood|font|glyph(?!R)|horiz|image|letter|lighting|marker(?!H|W|U)|overline|paint|pointer|shape|stop|strikethrough|stroke|text(?!L)|transform|underline|unicode|units|v|vector|vert|word|writing|x(?!C))[A-Z]/;
  var H2 = "undefined" != typeof document;
  var Z = function(n2) {
    return ("undefined" != typeof Symbol && "symbol" == typeof Symbol() ? /fil|che|rad/i : /fil|che|ra/i).test(n2);
  };
  x.prototype.isReactComponent = {}, ["componentWillMount", "componentWillReceiveProps", "componentWillUpdate"].forEach(function(t3) {
    Object.defineProperty(x.prototype, t3, { configurable: true, get: function() {
      return this["UNSAFE_" + t3];
    }, set: function(n2) {
      Object.defineProperty(this, t3, { configurable: true, writable: true, value: n2 });
    } });
  });
  var G2 = l.event;
  function J() {
  }
  function K() {
    return this.cancelBubble;
  }
  function Q() {
    return this.defaultPrevented;
  }
  l.event = function(n2) {
    return G2 && (n2 = G2(n2)), n2.persist = J, n2.isPropagationStopped = K, n2.isDefaultPrevented = Q, n2.nativeEvent = n2;
  };
  var X;
  var nn = { configurable: true, get: function() {
    return this.class;
  } };
  var tn = l.vnode;
  l.vnode = function(n2) {
    var t3 = n2.type, e3 = n2.props, u3 = e3;
    if ("string" == typeof t3) {
      var o2 = -1 === t3.indexOf("-");
      for (var i3 in u3 = {}, e3) {
        var l3 = e3[i3];
        H2 && "children" === i3 && "noscript" === t3 || "value" === i3 && "defaultValue" in e3 && null == l3 || ("defaultValue" === i3 && "value" in e3 && null == e3.value ? i3 = "value" : "download" === i3 && true === l3 ? l3 = "" : /ondoubleclick/i.test(i3) ? i3 = "ondblclick" : /^onchange(textarea|input)/i.test(i3 + t3) && !Z(e3.type) ? i3 = "oninput" : /^onfocus$/i.test(i3) ? i3 = "onfocusin" : /^onblur$/i.test(i3) ? i3 = "onfocusout" : /^on(Ani|Tra|Tou|BeforeInp|Compo)/.test(i3) ? i3 = i3.toLowerCase() : o2 && B2.test(i3) ? i3 = i3.replace(/[A-Z0-9]/g, "-$&").toLowerCase() : null === l3 && (l3 = void 0), /^oninput$/i.test(i3) && (i3 = i3.toLowerCase(), u3[i3] && (i3 = "oninputCapture")), u3[i3] = l3);
      }
      "select" == t3 && u3.multiple && Array.isArray(u3.value) && (u3.value = j(e3.children).forEach(function(n3) {
        n3.props.selected = -1 != u3.value.indexOf(n3.props.value);
      })), "select" == t3 && null != u3.defaultValue && (u3.value = j(e3.children).forEach(function(n3) {
        n3.props.selected = u3.multiple ? -1 != u3.defaultValue.indexOf(n3.props.value) : u3.defaultValue == n3.props.value;
      })), n2.props = u3, e3.class != e3.className && (nn.enumerable = "className" in e3, null != e3.className && (u3.class = e3.className), Object.defineProperty(u3, "className", nn));
    }
    n2.$$typeof = z2, tn && tn(n2);
  };
  var en = l.__r;
  l.__r = function(n2) {
    en && en(n2), X = n2.__c;
  };

  // ../ifitwala_ed/node_modules/@fullcalendar/core/internal-common.js
  var styleTexts = [];
  var styleEls = /* @__PURE__ */ new Map();
  function injectStyles(styleText) {
    styleTexts.push(styleText);
    styleEls.forEach((styleEl) => {
      appendStylesTo(styleEl, styleText);
    });
  }
  function ensureElHasStyles(el) {
    if (el.isConnected && el.getRootNode) {
      registerStylesRoot(el.getRootNode());
    }
  }
  function registerStylesRoot(rootNode) {
    let styleEl = styleEls.get(rootNode);
    if (!styleEl || !styleEl.isConnected) {
      styleEl = rootNode.querySelector("style[data-fullcalendar]");
      if (!styleEl) {
        styleEl = document.createElement("style");
        styleEl.setAttribute("data-fullcalendar", "");
        const nonce = getNonceValue();
        if (nonce) {
          styleEl.nonce = nonce;
        }
        const parentEl = rootNode === document ? document.head : rootNode;
        const insertBefore = rootNode === document ? parentEl.querySelector("script,link[rel=stylesheet],link[as=style],style") : parentEl.firstChild;
        parentEl.insertBefore(styleEl, insertBefore);
      }
      styleEls.set(rootNode, styleEl);
      hydrateStylesRoot(styleEl);
    }
  }
  function hydrateStylesRoot(styleEl) {
    for (const styleText of styleTexts) {
      appendStylesTo(styleEl, styleText);
    }
  }
  function appendStylesTo(styleEl, styleText) {
    const { sheet } = styleEl;
    const ruleCnt = sheet.cssRules.length;
    styleText.split("}").forEach((styleStr, i3) => {
      styleStr = styleStr.trim();
      if (styleStr) {
        sheet.insertRule(styleStr + "}", ruleCnt + i3);
      }
    });
  }
  var queriedNonceValue;
  function getNonceValue() {
    if (queriedNonceValue === void 0) {
      queriedNonceValue = queryNonceValue();
    }
    return queriedNonceValue;
  }
  function queryNonceValue() {
    const metaWithNonce = document.querySelector('meta[name="csp-nonce"]');
    if (metaWithNonce && metaWithNonce.hasAttribute("content")) {
      return metaWithNonce.getAttribute("content");
    }
    const elWithNonce = document.querySelector("script[nonce]");
    if (elWithNonce) {
      return elWithNonce.nonce || "";
    }
    return "";
  }
  if (typeof document !== "undefined") {
    registerStylesRoot(document);
  }
  var css_248z = ':root{--fc-small-font-size:.85em;--fc-page-bg-color:#fff;--fc-neutral-bg-color:hsla(0,0%,82%,.3);--fc-neutral-text-color:grey;--fc-border-color:#ddd;--fc-button-text-color:#fff;--fc-button-bg-color:#2c3e50;--fc-button-border-color:#2c3e50;--fc-button-hover-bg-color:#1e2b37;--fc-button-hover-border-color:#1a252f;--fc-button-active-bg-color:#1a252f;--fc-button-active-border-color:#151e27;--fc-event-bg-color:#3788d8;--fc-event-border-color:#3788d8;--fc-event-text-color:#fff;--fc-event-selected-overlay-color:rgba(0,0,0,.25);--fc-more-link-bg-color:#d0d0d0;--fc-more-link-text-color:inherit;--fc-event-resizer-thickness:8px;--fc-event-resizer-dot-total-width:8px;--fc-event-resizer-dot-border-width:1px;--fc-non-business-color:hsla(0,0%,84%,.3);--fc-bg-event-color:#8fdf82;--fc-bg-event-opacity:0.3;--fc-highlight-color:rgba(188,232,241,.3);--fc-today-bg-color:rgba(255,220,40,.15);--fc-now-indicator-color:red}.fc-not-allowed,.fc-not-allowed .fc-event{cursor:not-allowed}.fc{display:flex;flex-direction:column;font-size:1em}.fc,.fc *,.fc :after,.fc :before{box-sizing:border-box}.fc table{border-collapse:collapse;border-spacing:0;font-size:1em}.fc th{text-align:center}.fc td,.fc th{padding:0;vertical-align:top}.fc a[data-navlink]{cursor:pointer}.fc a[data-navlink]:hover{text-decoration:underline}.fc-direction-ltr{direction:ltr;text-align:left}.fc-direction-rtl{direction:rtl;text-align:right}.fc-theme-standard td,.fc-theme-standard th{border:1px solid var(--fc-border-color)}.fc-liquid-hack td,.fc-liquid-hack th{position:relative}@font-face{font-family:fcicons;font-style:normal;font-weight:400;src:url("data:application/x-font-ttf;charset=utf-8;base64,AAEAAAALAIAAAwAwT1MvMg8SBfAAAAC8AAAAYGNtYXAXVtKNAAABHAAAAFRnYXNwAAAAEAAAAXAAAAAIZ2x5ZgYydxIAAAF4AAAFNGhlYWQUJ7cIAAAGrAAAADZoaGVhB20DzAAABuQAAAAkaG10eCIABhQAAAcIAAAALGxvY2ED4AU6AAAHNAAAABhtYXhwAA8AjAAAB0wAAAAgbmFtZXsr690AAAdsAAABhnBvc3QAAwAAAAAI9AAAACAAAwPAAZAABQAAApkCzAAAAI8CmQLMAAAB6wAzAQkAAAAAAAAAAAAAAAAAAAABEAAAAAAAAAAAAAAAAAAAAABAAADpBgPA/8AAQAPAAEAAAAABAAAAAAAAAAAAAAAgAAAAAAADAAAAAwAAABwAAQADAAAAHAADAAEAAAAcAAQAOAAAAAoACAACAAIAAQAg6Qb//f//AAAAAAAg6QD//f//AAH/4xcEAAMAAQAAAAAAAAAAAAAAAQAB//8ADwABAAAAAAAAAAAAAgAANzkBAAAAAAEAAAAAAAAAAAACAAA3OQEAAAAAAQAAAAAAAAAAAAIAADc5AQAAAAABAWIAjQKeAskAEwAAJSc3NjQnJiIHAQYUFwEWMjc2NCcCnuLiDQ0MJAz/AA0NAQAMJAwNDcni4gwjDQwM/wANIwz/AA0NDCMNAAAAAQFiAI0CngLJABMAACUBNjQnASYiBwYUHwEHBhQXFjI3AZ4BAA0N/wAMJAwNDeLiDQ0MJAyNAQAMIw0BAAwMDSMM4uINIwwNDQAAAAIA4gC3Ax4CngATACcAACUnNzY0JyYiDwEGFB8BFjI3NjQnISc3NjQnJiIPAQYUHwEWMjc2NCcB87e3DQ0MIw3VDQ3VDSMMDQ0BK7e3DQ0MJAzVDQ3VDCQMDQ3zuLcMJAwNDdUNIwzWDAwNIwy4twwkDA0N1Q0jDNYMDA0jDAAAAgDiALcDHgKeABMAJwAAJTc2NC8BJiIHBhQfAQcGFBcWMjchNzY0LwEmIgcGFB8BBwYUFxYyNwJJ1Q0N1Q0jDA0Nt7cNDQwjDf7V1Q0N1QwkDA0Nt7cNDQwkDLfWDCMN1Q0NDCQMt7gMIw0MDNYMIw3VDQ0MJAy3uAwjDQwMAAADAFUAAAOrA1UAMwBoAHcAABMiBgcOAQcOAQcOARURFBYXHgEXHgEXHgEzITI2Nz4BNz4BNz4BNRE0JicuAScuAScuASMFITIWFx4BFx4BFx4BFREUBgcOAQcOAQcOASMhIiYnLgEnLgEnLgE1ETQ2Nz4BNz4BNz4BMxMhMjY1NCYjISIGFRQWM9UNGAwLFQkJDgUFBQUFBQ4JCRULDBgNAlYNGAwLFQkJDgUFBQUFBQ4JCRULDBgN/aoCVgQIBAQHAwMFAQIBAQIBBQMDBwQECAT9qgQIBAQHAwMFAQIBAQIBBQMDBwQECASAAVYRGRkR/qoRGRkRA1UFBAUOCQkVDAsZDf2rDRkLDBUJCA4FBQUFBQUOCQgVDAsZDQJVDRkLDBUJCQ4FBAVVAgECBQMCBwQECAX9qwQJAwQHAwMFAQICAgIBBQMDBwQDCQQCVQUIBAQHAgMFAgEC/oAZEhEZGRESGQAAAAADAFUAAAOrA1UAMwBoAIkAABMiBgcOAQcOAQcOARURFBYXHgEXHgEXHgEzITI2Nz4BNz4BNz4BNRE0JicuAScuAScuASMFITIWFx4BFx4BFx4BFREUBgcOAQcOAQcOASMhIiYnLgEnLgEnLgE1ETQ2Nz4BNz4BNz4BMxMzFRQWMzI2PQEzMjY1NCYrATU0JiMiBh0BIyIGFRQWM9UNGAwLFQkJDgUFBQUFBQ4JCRULDBgNAlYNGAwLFQkJDgUFBQUFBQ4JCRULDBgN/aoCVgQIBAQHAwMFAQIBAQIBBQMDBwQECAT9qgQIBAQHAwMFAQIBAQIBBQMDBwQECASAgBkSEhmAERkZEYAZEhIZgBEZGREDVQUEBQ4JCRUMCxkN/asNGQsMFQkIDgUFBQUFBQ4JCBUMCxkNAlUNGQsMFQkJDgUEBVUCAQIFAwIHBAQIBf2rBAkDBAcDAwUBAgICAgEFAwMHBAMJBAJVBQgEBAcCAwUCAQL+gIASGRkSgBkSERmAEhkZEoAZERIZAAABAOIAjQMeAskAIAAAExcHBhQXFjI/ARcWMjc2NC8BNzY0JyYiDwEnJiIHBhQX4uLiDQ0MJAzi4gwkDA0N4uINDQwkDOLiDCQMDQ0CjeLiDSMMDQ3h4Q0NDCMN4uIMIw0MDOLiDAwNIwwAAAABAAAAAQAAa5n0y18PPPUACwQAAAAAANivOVsAAAAA2K85WwAAAAADqwNVAAAACAACAAAAAAAAAAEAAAPA/8AAAAQAAAAAAAOrAAEAAAAAAAAAAAAAAAAAAAALBAAAAAAAAAAAAAAAAgAAAAQAAWIEAAFiBAAA4gQAAOIEAABVBAAAVQQAAOIAAAAAAAoAFAAeAEQAagCqAOoBngJkApoAAQAAAAsAigADAAAAAAACAAAAAAAAAAAAAAAAAAAAAAAAAA4ArgABAAAAAAABAAcAAAABAAAAAAACAAcAYAABAAAAAAADAAcANgABAAAAAAAEAAcAdQABAAAAAAAFAAsAFQABAAAAAAAGAAcASwABAAAAAAAKABoAigADAAEECQABAA4ABwADAAEECQACAA4AZwADAAEECQADAA4APQADAAEECQAEAA4AfAADAAEECQAFABYAIAADAAEECQAGAA4AUgADAAEECQAKADQApGZjaWNvbnMAZgBjAGkAYwBvAG4Ac1ZlcnNpb24gMS4wAFYAZQByAHMAaQBvAG4AIAAxAC4AMGZjaWNvbnMAZgBjAGkAYwBvAG4Ac2ZjaWNvbnMAZgBjAGkAYwBvAG4Ac1JlZ3VsYXIAUgBlAGcAdQBsAGEAcmZjaWNvbnMAZgBjAGkAYwBvAG4Ac0ZvbnQgZ2VuZXJhdGVkIGJ5IEljb01vb24uAEYAbwBuAHQAIABnAGUAbgBlAHIAYQB0AGUAZAAgAGIAeQAgAEkAYwBvAE0AbwBvAG4ALgAAAAMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=") format("truetype")}.fc-icon{speak:none;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;display:inline-block;font-family:fcicons!important;font-style:normal;font-variant:normal;font-weight:400;height:1em;line-height:1;text-align:center;text-transform:none;-webkit-user-select:none;-moz-user-select:none;user-select:none;width:1em}.fc-icon-chevron-left:before{content:"\\e900"}.fc-icon-chevron-right:before{content:"\\e901"}.fc-icon-chevrons-left:before{content:"\\e902"}.fc-icon-chevrons-right:before{content:"\\e903"}.fc-icon-minus-square:before{content:"\\e904"}.fc-icon-plus-square:before{content:"\\e905"}.fc-icon-x:before{content:"\\e906"}.fc .fc-button{border-radius:0;font-family:inherit;font-size:inherit;line-height:inherit;margin:0;overflow:visible;text-transform:none}.fc .fc-button:focus{outline:1px dotted;outline:5px auto -webkit-focus-ring-color}.fc .fc-button{-webkit-appearance:button}.fc .fc-button:not(:disabled){cursor:pointer}.fc .fc-button{background-color:transparent;border:1px solid transparent;border-radius:.25em;display:inline-block;font-size:1em;font-weight:400;line-height:1.5;padding:.4em .65em;text-align:center;-webkit-user-select:none;-moz-user-select:none;user-select:none;vertical-align:middle}.fc .fc-button:hover{text-decoration:none}.fc .fc-button:focus{box-shadow:0 0 0 .2rem rgba(44,62,80,.25);outline:0}.fc .fc-button:disabled{opacity:.65}.fc .fc-button-primary{background-color:var(--fc-button-bg-color);border-color:var(--fc-button-border-color);color:var(--fc-button-text-color)}.fc .fc-button-primary:hover{background-color:var(--fc-button-hover-bg-color);border-color:var(--fc-button-hover-border-color);color:var(--fc-button-text-color)}.fc .fc-button-primary:disabled{background-color:var(--fc-button-bg-color);border-color:var(--fc-button-border-color);color:var(--fc-button-text-color)}.fc .fc-button-primary:focus{box-shadow:0 0 0 .2rem rgba(76,91,106,.5)}.fc .fc-button-primary:not(:disabled).fc-button-active,.fc .fc-button-primary:not(:disabled):active{background-color:var(--fc-button-active-bg-color);border-color:var(--fc-button-active-border-color);color:var(--fc-button-text-color)}.fc .fc-button-primary:not(:disabled).fc-button-active:focus,.fc .fc-button-primary:not(:disabled):active:focus{box-shadow:0 0 0 .2rem rgba(76,91,106,.5)}.fc .fc-button .fc-icon{font-size:1.5em;vertical-align:middle}.fc .fc-button-group{display:inline-flex;position:relative;vertical-align:middle}.fc .fc-button-group>.fc-button{flex:1 1 auto;position:relative}.fc .fc-button-group>.fc-button.fc-button-active,.fc .fc-button-group>.fc-button:active,.fc .fc-button-group>.fc-button:focus,.fc .fc-button-group>.fc-button:hover{z-index:1}.fc-direction-ltr .fc-button-group>.fc-button:not(:first-child){border-bottom-left-radius:0;border-top-left-radius:0;margin-left:-1px}.fc-direction-ltr .fc-button-group>.fc-button:not(:last-child){border-bottom-right-radius:0;border-top-right-radius:0}.fc-direction-rtl .fc-button-group>.fc-button:not(:first-child){border-bottom-right-radius:0;border-top-right-radius:0;margin-right:-1px}.fc-direction-rtl .fc-button-group>.fc-button:not(:last-child){border-bottom-left-radius:0;border-top-left-radius:0}.fc .fc-toolbar{align-items:center;display:flex;justify-content:space-between}.fc .fc-toolbar.fc-header-toolbar{margin-bottom:1.5em}.fc .fc-toolbar.fc-footer-toolbar{margin-top:1.5em}.fc .fc-toolbar-title{font-size:1.75em;margin:0}.fc-direction-ltr .fc-toolbar>*>:not(:first-child){margin-left:.75em}.fc-direction-rtl .fc-toolbar>*>:not(:first-child){margin-right:.75em}.fc-direction-rtl .fc-toolbar-ltr{flex-direction:row-reverse}.fc .fc-scroller{-webkit-overflow-scrolling:touch;position:relative}.fc .fc-scroller-liquid{height:100%}.fc .fc-scroller-liquid-absolute{bottom:0;left:0;position:absolute;right:0;top:0}.fc .fc-scroller-harness{direction:ltr;overflow:hidden;position:relative}.fc .fc-scroller-harness-liquid{height:100%}.fc-direction-rtl .fc-scroller-harness>.fc-scroller{direction:rtl}.fc-theme-standard .fc-scrollgrid{border:1px solid var(--fc-border-color)}.fc .fc-scrollgrid,.fc .fc-scrollgrid table{table-layout:fixed;width:100%}.fc .fc-scrollgrid table{border-left-style:hidden;border-right-style:hidden;border-top-style:hidden}.fc .fc-scrollgrid{border-bottom-width:0;border-collapse:separate;border-right-width:0}.fc .fc-scrollgrid-liquid{height:100%}.fc .fc-scrollgrid-section,.fc .fc-scrollgrid-section table,.fc .fc-scrollgrid-section>td{height:1px}.fc .fc-scrollgrid-section-liquid>td{height:100%}.fc .fc-scrollgrid-section>*{border-left-width:0;border-top-width:0}.fc .fc-scrollgrid-section-footer>*,.fc .fc-scrollgrid-section-header>*{border-bottom-width:0}.fc .fc-scrollgrid-section-body table,.fc .fc-scrollgrid-section-footer table{border-bottom-style:hidden}.fc .fc-scrollgrid-section-sticky>*{background:var(--fc-page-bg-color);position:sticky;z-index:3}.fc .fc-scrollgrid-section-header.fc-scrollgrid-section-sticky>*{top:0}.fc .fc-scrollgrid-section-footer.fc-scrollgrid-section-sticky>*{bottom:0}.fc .fc-scrollgrid-sticky-shim{height:1px;margin-bottom:-1px}.fc-sticky{position:sticky}.fc .fc-view-harness{flex-grow:1;position:relative}.fc .fc-view-harness-active>.fc-view{bottom:0;left:0;position:absolute;right:0;top:0}.fc .fc-col-header-cell-cushion{display:inline-block;padding:2px 4px}.fc .fc-bg-event,.fc .fc-highlight,.fc .fc-non-business{bottom:0;left:0;position:absolute;right:0;top:0}.fc .fc-non-business{background:var(--fc-non-business-color)}.fc .fc-bg-event{background:var(--fc-bg-event-color);opacity:var(--fc-bg-event-opacity)}.fc .fc-bg-event .fc-event-title{font-size:var(--fc-small-font-size);font-style:italic;margin:.5em}.fc .fc-highlight{background:var(--fc-highlight-color)}.fc .fc-cell-shaded,.fc .fc-day-disabled{background:var(--fc-neutral-bg-color)}a.fc-event,a.fc-event:hover{text-decoration:none}.fc-event.fc-event-draggable,.fc-event[href]{cursor:pointer}.fc-event .fc-event-main{position:relative;z-index:2}.fc-event-dragging:not(.fc-event-selected){opacity:.75}.fc-event-dragging.fc-event-selected{box-shadow:0 2px 7px rgba(0,0,0,.3)}.fc-event .fc-event-resizer{display:none;position:absolute;z-index:4}.fc-event-selected .fc-event-resizer,.fc-event:hover .fc-event-resizer{display:block}.fc-event-selected .fc-event-resizer{background:var(--fc-page-bg-color);border-color:inherit;border-radius:calc(var(--fc-event-resizer-dot-total-width)/2);border-style:solid;border-width:var(--fc-event-resizer-dot-border-width);height:var(--fc-event-resizer-dot-total-width);width:var(--fc-event-resizer-dot-total-width)}.fc-event-selected .fc-event-resizer:before{bottom:-20px;content:"";left:-20px;position:absolute;right:-20px;top:-20px}.fc-event-selected,.fc-event:focus{box-shadow:0 2px 5px rgba(0,0,0,.2)}.fc-event-selected:before,.fc-event:focus:before{bottom:0;content:"";left:0;position:absolute;right:0;top:0;z-index:3}.fc-event-selected:after,.fc-event:focus:after{background:var(--fc-event-selected-overlay-color);bottom:-1px;content:"";left:-1px;position:absolute;right:-1px;top:-1px;z-index:1}.fc-h-event{background-color:var(--fc-event-bg-color);border:1px solid var(--fc-event-border-color);display:block}.fc-h-event .fc-event-main{color:var(--fc-event-text-color)}.fc-h-event .fc-event-main-frame{display:flex}.fc-h-event .fc-event-time{max-width:100%;overflow:hidden}.fc-h-event .fc-event-title-container{flex-grow:1;flex-shrink:1;min-width:0}.fc-h-event .fc-event-title{display:inline-block;left:0;max-width:100%;overflow:hidden;right:0;vertical-align:top}.fc-h-event.fc-event-selected:before{bottom:-10px;top:-10px}.fc-direction-ltr .fc-daygrid-block-event:not(.fc-event-start),.fc-direction-rtl .fc-daygrid-block-event:not(.fc-event-end){border-bottom-left-radius:0;border-left-width:0;border-top-left-radius:0}.fc-direction-ltr .fc-daygrid-block-event:not(.fc-event-end),.fc-direction-rtl .fc-daygrid-block-event:not(.fc-event-start){border-bottom-right-radius:0;border-right-width:0;border-top-right-radius:0}.fc-h-event:not(.fc-event-selected) .fc-event-resizer{bottom:0;top:0;width:var(--fc-event-resizer-thickness)}.fc-direction-ltr .fc-h-event:not(.fc-event-selected) .fc-event-resizer-start,.fc-direction-rtl .fc-h-event:not(.fc-event-selected) .fc-event-resizer-end{cursor:w-resize;left:calc(var(--fc-event-resizer-thickness)*-.5)}.fc-direction-ltr .fc-h-event:not(.fc-event-selected) .fc-event-resizer-end,.fc-direction-rtl .fc-h-event:not(.fc-event-selected) .fc-event-resizer-start{cursor:e-resize;right:calc(var(--fc-event-resizer-thickness)*-.5)}.fc-h-event.fc-event-selected .fc-event-resizer{margin-top:calc(var(--fc-event-resizer-dot-total-width)*-.5);top:50%}.fc-direction-ltr .fc-h-event.fc-event-selected .fc-event-resizer-start,.fc-direction-rtl .fc-h-event.fc-event-selected .fc-event-resizer-end{left:calc(var(--fc-event-resizer-dot-total-width)*-.5)}.fc-direction-ltr .fc-h-event.fc-event-selected .fc-event-resizer-end,.fc-direction-rtl .fc-h-event.fc-event-selected .fc-event-resizer-start{right:calc(var(--fc-event-resizer-dot-total-width)*-.5)}.fc .fc-popover{box-shadow:0 2px 6px rgba(0,0,0,.15);position:absolute;z-index:9999}.fc .fc-popover-header{align-items:center;display:flex;flex-direction:row;justify-content:space-between;padding:3px 4px}.fc .fc-popover-title{margin:0 2px}.fc .fc-popover-close{cursor:pointer;font-size:1.1em;opacity:.65}.fc-theme-standard .fc-popover{background:var(--fc-page-bg-color);border:1px solid var(--fc-border-color)}.fc-theme-standard .fc-popover-header{background:var(--fc-neutral-bg-color)}';
  injectStyles(css_248z);
  var DelayedRunner = class {
    constructor(drainedOption) {
      this.drainedOption = drainedOption;
      this.isRunning = false;
      this.isDirty = false;
      this.pauseDepths = {};
      this.timeoutId = 0;
    }
    request(delay) {
      this.isDirty = true;
      if (!this.isPaused()) {
        this.clearTimeout();
        if (delay == null) {
          this.tryDrain();
        } else {
          this.timeoutId = setTimeout(
            this.tryDrain.bind(this),
            delay
          );
        }
      }
    }
    pause(scope = "") {
      let { pauseDepths } = this;
      pauseDepths[scope] = (pauseDepths[scope] || 0) + 1;
      this.clearTimeout();
    }
    resume(scope = "", force) {
      let { pauseDepths } = this;
      if (scope in pauseDepths) {
        if (force) {
          delete pauseDepths[scope];
        } else {
          pauseDepths[scope] -= 1;
          let depth = pauseDepths[scope];
          if (depth <= 0) {
            delete pauseDepths[scope];
          }
        }
        this.tryDrain();
      }
    }
    isPaused() {
      return Object.keys(this.pauseDepths).length;
    }
    tryDrain() {
      if (!this.isRunning && !this.isPaused()) {
        this.isRunning = true;
        while (this.isDirty) {
          this.isDirty = false;
          this.drained();
        }
        this.isRunning = false;
      }
    }
    clear() {
      this.clearTimeout();
      this.isDirty = false;
      this.pauseDepths = {};
    }
    clearTimeout() {
      if (this.timeoutId) {
        clearTimeout(this.timeoutId);
        this.timeoutId = 0;
      }
    }
    drained() {
      if (this.drainedOption) {
        this.drainedOption();
      }
    }
  };
  function removeElement(el) {
    if (el.parentNode) {
      el.parentNode.removeChild(el);
    }
  }
  function elementClosest(el, selector) {
    if (el.closest) {
      return el.closest(selector);
    }
    if (!document.documentElement.contains(el)) {
      return null;
    }
    do {
      if (elementMatches(el, selector)) {
        return el;
      }
      el = el.parentElement || el.parentNode;
    } while (el !== null && el.nodeType === 1);
    return null;
  }
  function elementMatches(el, selector) {
    let method = el.matches || el.matchesSelector || el.msMatchesSelector;
    return method.call(el, selector);
  }
  function findElements(container, selector) {
    let containers = container instanceof HTMLElement ? [container] : container;
    let allMatches = [];
    for (let i3 = 0; i3 < containers.length; i3 += 1) {
      let matches = containers[i3].querySelectorAll(selector);
      for (let j4 = 0; j4 < matches.length; j4 += 1) {
        allMatches.push(matches[j4]);
      }
    }
    return allMatches;
  }
  var PIXEL_PROP_RE = /(top|left|right|bottom|width|height)$/i;
  function applyStyle(el, props) {
    for (let propName in props) {
      applyStyleProp(el, propName, props[propName]);
    }
  }
  function applyStyleProp(el, name, val) {
    if (val == null) {
      el.style[name] = "";
    } else if (typeof val === "number" && PIXEL_PROP_RE.test(name)) {
      el.style[name] = `${val}px`;
    } else {
      el.style[name] = val;
    }
  }
  function getEventTargetViaRoot(ev) {
    var _a, _b;
    return (_b = (_a = ev.composedPath) === null || _a === void 0 ? void 0 : _a.call(ev)[0]) !== null && _b !== void 0 ? _b : ev.target;
  }
  var guid$1 = 0;
  function getUniqueDomId() {
    guid$1 += 1;
    return "fc-dom-" + guid$1;
  }
  function buildDelegationHandler(selector, handler) {
    return (ev) => {
      let matchedChild = elementClosest(ev.target, selector);
      if (matchedChild) {
        handler.call(matchedChild, ev, matchedChild);
      }
    };
  }
  function listenBySelector(container, eventType, selector, handler) {
    let attachedHandler = buildDelegationHandler(selector, handler);
    container.addEventListener(eventType, attachedHandler);
    return () => {
      container.removeEventListener(eventType, attachedHandler);
    };
  }
  function listenToHoverBySelector(container, selector, onMouseEnter, onMouseLeave) {
    let currentMatchedChild;
    return listenBySelector(container, "mouseover", selector, (mouseOverEv, matchedChild) => {
      if (matchedChild !== currentMatchedChild) {
        currentMatchedChild = matchedChild;
        onMouseEnter(mouseOverEv, matchedChild);
        let realOnMouseLeave = (mouseLeaveEv) => {
          currentMatchedChild = null;
          onMouseLeave(mouseLeaveEv, matchedChild);
          matchedChild.removeEventListener("mouseleave", realOnMouseLeave);
        };
        matchedChild.addEventListener("mouseleave", realOnMouseLeave);
      }
    });
  }
  function createAriaClickAttrs(handler) {
    return Object.assign({ onClick: handler }, createAriaKeyboardAttrs(handler));
  }
  function createAriaKeyboardAttrs(handler) {
    return {
      tabIndex: 0,
      onKeyDown(ev) {
        if (ev.key === "Enter" || ev.key === " ") {
          handler(ev);
          ev.preventDefault();
        }
      }
    };
  }
  var guidNumber = 0;
  function guid() {
    guidNumber += 1;
    return String(guidNumber);
  }
  function parseFieldSpecs(input) {
    let specs = [];
    let tokens = [];
    let i3;
    let token;
    if (typeof input === "string") {
      tokens = input.split(/\s*,\s*/);
    } else if (typeof input === "function") {
      tokens = [input];
    } else if (Array.isArray(input)) {
      tokens = input;
    }
    for (i3 = 0; i3 < tokens.length; i3 += 1) {
      token = tokens[i3];
      if (typeof token === "string") {
        specs.push(token.charAt(0) === "-" ? { field: token.substring(1), order: -1 } : { field: token, order: 1 });
      } else if (typeof token === "function") {
        specs.push({ func: token });
      }
    }
    return specs;
  }
  function compareByFieldSpecs(obj0, obj1, fieldSpecs) {
    let i3;
    let cmp;
    for (i3 = 0; i3 < fieldSpecs.length; i3 += 1) {
      cmp = compareByFieldSpec(obj0, obj1, fieldSpecs[i3]);
      if (cmp) {
        return cmp;
      }
    }
    return 0;
  }
  function compareByFieldSpec(obj0, obj1, fieldSpec) {
    if (fieldSpec.func) {
      return fieldSpec.func(obj0, obj1);
    }
    return flexibleCompare(obj0[fieldSpec.field], obj1[fieldSpec.field]) * (fieldSpec.order || 1);
  }
  function flexibleCompare(a3, b3) {
    if (!a3 && !b3) {
      return 0;
    }
    if (b3 == null) {
      return -1;
    }
    if (a3 == null) {
      return 1;
    }
    if (typeof a3 === "string" || typeof b3 === "string") {
      return String(a3).localeCompare(String(b3));
    }
    return a3 - b3;
  }
  function padStart(val, len) {
    let s3 = String(val);
    return "000".substr(0, len - s3.length) + s3;
  }
  function formatWithOrdinals(formatter, args, fallbackText) {
    if (typeof formatter === "function") {
      return formatter(...args);
    }
    if (typeof formatter === "string") {
      return args.reduce((str, arg, index4) => str.replace("$" + index4, arg || ""), formatter);
    }
    return fallbackText;
  }
  function isInt(n2) {
    return n2 % 1 === 0;
  }
  function computeSmallestCellWidth(cellEl) {
    let allWidthEl = cellEl.querySelector(".fc-scrollgrid-shrink-frame");
    let contentWidthEl = cellEl.querySelector(".fc-scrollgrid-shrink-cushion");
    if (!allWidthEl) {
      throw new Error("needs fc-scrollgrid-shrink-frame className");
    }
    if (!contentWidthEl) {
      throw new Error("needs fc-scrollgrid-shrink-cushion className");
    }
    return cellEl.getBoundingClientRect().width - allWidthEl.getBoundingClientRect().width + contentWidthEl.getBoundingClientRect().width;
  }
  var INTERNAL_UNITS = ["years", "months", "days", "milliseconds"];
  var PARSE_RE = /^(-?)(?:(\d+)\.)?(\d+):(\d\d)(?::(\d\d)(?:\.(\d\d\d))?)?/;
  function createDuration(input, unit) {
    if (typeof input === "string") {
      return parseString(input);
    }
    if (typeof input === "object" && input) {
      return parseObject(input);
    }
    if (typeof input === "number") {
      return parseObject({ [unit || "milliseconds"]: input });
    }
    return null;
  }
  function parseString(s3) {
    let m3 = PARSE_RE.exec(s3);
    if (m3) {
      let sign = m3[1] ? -1 : 1;
      return {
        years: 0,
        months: 0,
        days: sign * (m3[2] ? parseInt(m3[2], 10) : 0),
        milliseconds: sign * ((m3[3] ? parseInt(m3[3], 10) : 0) * 60 * 60 * 1e3 + (m3[4] ? parseInt(m3[4], 10) : 0) * 60 * 1e3 + (m3[5] ? parseInt(m3[5], 10) : 0) * 1e3 + (m3[6] ? parseInt(m3[6], 10) : 0))
      };
    }
    return null;
  }
  function parseObject(obj) {
    let duration = {
      years: obj.years || obj.year || 0,
      months: obj.months || obj.month || 0,
      days: obj.days || obj.day || 0,
      milliseconds: (obj.hours || obj.hour || 0) * 60 * 60 * 1e3 + (obj.minutes || obj.minute || 0) * 60 * 1e3 + (obj.seconds || obj.second || 0) * 1e3 + (obj.milliseconds || obj.millisecond || obj.ms || 0)
    };
    let weeks = obj.weeks || obj.week;
    if (weeks) {
      duration.days += weeks * 7;
      duration.specifiedWeeks = true;
    }
    return duration;
  }
  function durationsEqual(d0, d1) {
    return d0.years === d1.years && d0.months === d1.months && d0.days === d1.days && d0.milliseconds === d1.milliseconds;
  }
  function addDurations(d0, d1) {
    return {
      years: d0.years + d1.years,
      months: d0.months + d1.months,
      days: d0.days + d1.days,
      milliseconds: d0.milliseconds + d1.milliseconds
    };
  }
  function subtractDurations(d1, d0) {
    return {
      years: d1.years - d0.years,
      months: d1.months - d0.months,
      days: d1.days - d0.days,
      milliseconds: d1.milliseconds - d0.milliseconds
    };
  }
  function multiplyDuration(d2, n2) {
    return {
      years: d2.years * n2,
      months: d2.months * n2,
      days: d2.days * n2,
      milliseconds: d2.milliseconds * n2
    };
  }
  function asRoughYears(dur) {
    return asRoughDays(dur) / 365;
  }
  function asRoughMonths(dur) {
    return asRoughDays(dur) / 30;
  }
  function asRoughDays(dur) {
    return asRoughMs(dur) / 864e5;
  }
  function asRoughMs(dur) {
    return dur.years * (365 * 864e5) + dur.months * (30 * 864e5) + dur.days * 864e5 + dur.milliseconds;
  }
  function wholeDivideDurations(numerator, denominator) {
    let res = null;
    for (let i3 = 0; i3 < INTERNAL_UNITS.length; i3 += 1) {
      let unit = INTERNAL_UNITS[i3];
      if (denominator[unit]) {
        let localRes = numerator[unit] / denominator[unit];
        if (!isInt(localRes) || res !== null && res !== localRes) {
          return null;
        }
        res = localRes;
      } else if (numerator[unit]) {
        return null;
      }
    }
    return res;
  }
  function greatestDurationDenominator(dur) {
    let ms = dur.milliseconds;
    if (ms) {
      if (ms % 1e3 !== 0) {
        return { unit: "millisecond", value: ms };
      }
      if (ms % (1e3 * 60) !== 0) {
        return { unit: "second", value: ms / 1e3 };
      }
      if (ms % (1e3 * 60 * 60) !== 0) {
        return { unit: "minute", value: ms / (1e3 * 60) };
      }
      if (ms) {
        return { unit: "hour", value: ms / (1e3 * 60 * 60) };
      }
    }
    if (dur.days) {
      if (dur.specifiedWeeks && dur.days % 7 === 0) {
        return { unit: "week", value: dur.days / 7 };
      }
      return { unit: "day", value: dur.days };
    }
    if (dur.months) {
      return { unit: "month", value: dur.months };
    }
    if (dur.years) {
      return { unit: "year", value: dur.years };
    }
    return { unit: "millisecond", value: 0 };
  }
  function isArraysEqual(a0, a1, equalityFunc) {
    if (a0 === a1) {
      return true;
    }
    let len = a0.length;
    let i3;
    if (len !== a1.length) {
      return false;
    }
    for (i3 = 0; i3 < len; i3 += 1) {
      if (!(equalityFunc ? equalityFunc(a0[i3], a1[i3]) : a0[i3] === a1[i3])) {
        return false;
      }
    }
    return true;
  }
  var DAY_IDS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];
  function addWeeks(m3, n2) {
    let a3 = dateToUtcArray(m3);
    a3[2] += n2 * 7;
    return arrayToUtcDate(a3);
  }
  function addDays(m3, n2) {
    let a3 = dateToUtcArray(m3);
    a3[2] += n2;
    return arrayToUtcDate(a3);
  }
  function addMs(m3, n2) {
    let a3 = dateToUtcArray(m3);
    a3[6] += n2;
    return arrayToUtcDate(a3);
  }
  function diffWeeks(m0, m1) {
    return diffDays(m0, m1) / 7;
  }
  function diffDays(m0, m1) {
    return (m1.valueOf() - m0.valueOf()) / (1e3 * 60 * 60 * 24);
  }
  function diffHours(m0, m1) {
    return (m1.valueOf() - m0.valueOf()) / (1e3 * 60 * 60);
  }
  function diffMinutes(m0, m1) {
    return (m1.valueOf() - m0.valueOf()) / (1e3 * 60);
  }
  function diffSeconds(m0, m1) {
    return (m1.valueOf() - m0.valueOf()) / 1e3;
  }
  function diffDayAndTime(m0, m1) {
    let m0day = startOfDay(m0);
    let m1day = startOfDay(m1);
    return {
      years: 0,
      months: 0,
      days: Math.round(diffDays(m0day, m1day)),
      milliseconds: m1.valueOf() - m1day.valueOf() - (m0.valueOf() - m0day.valueOf())
    };
  }
  function diffWholeWeeks(m0, m1) {
    let d2 = diffWholeDays(m0, m1);
    if (d2 !== null && d2 % 7 === 0) {
      return d2 / 7;
    }
    return null;
  }
  function diffWholeDays(m0, m1) {
    if (timeAsMs(m0) === timeAsMs(m1)) {
      return Math.round(diffDays(m0, m1));
    }
    return null;
  }
  function startOfDay(m3) {
    return arrayToUtcDate([
      m3.getUTCFullYear(),
      m3.getUTCMonth(),
      m3.getUTCDate()
    ]);
  }
  function startOfHour(m3) {
    return arrayToUtcDate([
      m3.getUTCFullYear(),
      m3.getUTCMonth(),
      m3.getUTCDate(),
      m3.getUTCHours()
    ]);
  }
  function startOfMinute(m3) {
    return arrayToUtcDate([
      m3.getUTCFullYear(),
      m3.getUTCMonth(),
      m3.getUTCDate(),
      m3.getUTCHours(),
      m3.getUTCMinutes()
    ]);
  }
  function startOfSecond(m3) {
    return arrayToUtcDate([
      m3.getUTCFullYear(),
      m3.getUTCMonth(),
      m3.getUTCDate(),
      m3.getUTCHours(),
      m3.getUTCMinutes(),
      m3.getUTCSeconds()
    ]);
  }
  function weekOfYear(marker, dow, doy) {
    let y3 = marker.getUTCFullYear();
    let w4 = weekOfGivenYear(marker, y3, dow, doy);
    if (w4 < 1) {
      return weekOfGivenYear(marker, y3 - 1, dow, doy);
    }
    let nextW = weekOfGivenYear(marker, y3 + 1, dow, doy);
    if (nextW >= 1) {
      return Math.min(w4, nextW);
    }
    return w4;
  }
  function weekOfGivenYear(marker, year, dow, doy) {
    let firstWeekStart = arrayToUtcDate([year, 0, 1 + firstWeekOffset(year, dow, doy)]);
    let dayStart = startOfDay(marker);
    let days = Math.round(diffDays(firstWeekStart, dayStart));
    return Math.floor(days / 7) + 1;
  }
  function firstWeekOffset(year, dow, doy) {
    let fwd = 7 + dow - doy;
    let fwdlw = (7 + arrayToUtcDate([year, 0, fwd]).getUTCDay() - dow) % 7;
    return -fwdlw + fwd - 1;
  }
  function dateToLocalArray(date) {
    return [
      date.getFullYear(),
      date.getMonth(),
      date.getDate(),
      date.getHours(),
      date.getMinutes(),
      date.getSeconds(),
      date.getMilliseconds()
    ];
  }
  function arrayToLocalDate(a3) {
    return new Date(
      a3[0],
      a3[1] || 0,
      a3[2] == null ? 1 : a3[2],
      a3[3] || 0,
      a3[4] || 0,
      a3[5] || 0
    );
  }
  function dateToUtcArray(date) {
    return [
      date.getUTCFullYear(),
      date.getUTCMonth(),
      date.getUTCDate(),
      date.getUTCHours(),
      date.getUTCMinutes(),
      date.getUTCSeconds(),
      date.getUTCMilliseconds()
    ];
  }
  function arrayToUtcDate(a3) {
    if (a3.length === 1) {
      a3 = a3.concat([0]);
    }
    return new Date(Date.UTC(...a3));
  }
  function isValidDate(m3) {
    return !isNaN(m3.valueOf());
  }
  function timeAsMs(m3) {
    return m3.getUTCHours() * 1e3 * 60 * 60 + m3.getUTCMinutes() * 1e3 * 60 + m3.getUTCSeconds() * 1e3 + m3.getUTCMilliseconds();
  }
  function buildIsoString(marker, timeZoneOffset, stripZeroTime = false) {
    let s3 = marker.toISOString();
    s3 = s3.replace(".000", "");
    if (stripZeroTime) {
      s3 = s3.replace("T00:00:00Z", "");
    }
    if (s3.length > 10) {
      if (timeZoneOffset == null) {
        s3 = s3.replace("Z", "");
      } else if (timeZoneOffset !== 0) {
        s3 = s3.replace("Z", formatTimeZoneOffset(timeZoneOffset, true));
      }
    }
    return s3;
  }
  function formatDayString(marker) {
    return marker.toISOString().replace(/T.*$/, "");
  }
  function formatIsoMonthStr(marker) {
    return marker.toISOString().match(/^\d{4}-\d{2}/)[0];
  }
  function formatIsoTimeString(marker) {
    return padStart(marker.getUTCHours(), 2) + ":" + padStart(marker.getUTCMinutes(), 2) + ":" + padStart(marker.getUTCSeconds(), 2);
  }
  function formatTimeZoneOffset(minutes, doIso = false) {
    let sign = minutes < 0 ? "-" : "+";
    let abs = Math.abs(minutes);
    let hours = Math.floor(abs / 60);
    let mins = Math.round(abs % 60);
    if (doIso) {
      return `${sign + padStart(hours, 2)}:${padStart(mins, 2)}`;
    }
    return `GMT${sign}${hours}${mins ? `:${padStart(mins, 2)}` : ""}`;
  }
  function memoize(workerFunc, resEquality, teardownFunc) {
    let currentArgs;
    let currentRes;
    return function(...newArgs) {
      if (!currentArgs) {
        currentRes = workerFunc.apply(this, newArgs);
      } else if (!isArraysEqual(currentArgs, newArgs)) {
        if (teardownFunc) {
          teardownFunc(currentRes);
        }
        let res = workerFunc.apply(this, newArgs);
        if (!resEquality || !resEquality(res, currentRes)) {
          currentRes = res;
        }
      }
      currentArgs = newArgs;
      return currentRes;
    };
  }
  function memoizeObjArg(workerFunc, resEquality, teardownFunc) {
    let currentArg;
    let currentRes;
    return (newArg) => {
      if (!currentArg) {
        currentRes = workerFunc.call(this, newArg);
      } else if (!isPropsEqual(currentArg, newArg)) {
        if (teardownFunc) {
          teardownFunc(currentRes);
        }
        let res = workerFunc.call(this, newArg);
        if (!resEquality || !resEquality(res, currentRes)) {
          currentRes = res;
        }
      }
      currentArg = newArg;
      return currentRes;
    };
  }
  var EXTENDED_SETTINGS_AND_SEVERITIES = {
    week: 3,
    separator: 9,
    omitZeroMinute: 9,
    meridiem: 9,
    omitCommas: 9
  };
  var STANDARD_DATE_PROP_SEVERITIES = {
    timeZoneName: 7,
    era: 6,
    year: 5,
    month: 4,
    day: 2,
    weekday: 2,
    hour: 1,
    minute: 1,
    second: 1
  };
  var MERIDIEM_RE = /\s*([ap])\.?m\.?/i;
  var COMMA_RE = /,/g;
  var MULTI_SPACE_RE = /\s+/g;
  var LTR_RE = /\u200e/g;
  var UTC_RE = /UTC|GMT/;
  var NativeFormatter = class {
    constructor(formatSettings) {
      let standardDateProps = {};
      let extendedSettings = {};
      let smallestUnitNum = 9;
      for (let name in formatSettings) {
        if (name in EXTENDED_SETTINGS_AND_SEVERITIES) {
          extendedSettings[name] = formatSettings[name];
          const severity = EXTENDED_SETTINGS_AND_SEVERITIES[name];
          if (severity < 9) {
            smallestUnitNum = Math.min(EXTENDED_SETTINGS_AND_SEVERITIES[name], smallestUnitNum);
          }
        } else {
          standardDateProps[name] = formatSettings[name];
          if (name in STANDARD_DATE_PROP_SEVERITIES) {
            smallestUnitNum = Math.min(STANDARD_DATE_PROP_SEVERITIES[name], smallestUnitNum);
          }
        }
      }
      this.standardDateProps = standardDateProps;
      this.extendedSettings = extendedSettings;
      this.smallestUnitNum = smallestUnitNum;
      this.buildFormattingFunc = memoize(buildFormattingFunc);
    }
    format(date, context) {
      return this.buildFormattingFunc(this.standardDateProps, this.extendedSettings, context)(date);
    }
    formatRange(start, end, context, betterDefaultSeparator) {
      let { standardDateProps, extendedSettings } = this;
      let diffSeverity = computeMarkerDiffSeverity(start.marker, end.marker, context.calendarSystem);
      if (!diffSeverity) {
        return this.format(start, context);
      }
      let biggestUnitForPartial = diffSeverity;
      if (biggestUnitForPartial > 1 && (standardDateProps.year === "numeric" || standardDateProps.year === "2-digit") && (standardDateProps.month === "numeric" || standardDateProps.month === "2-digit") && (standardDateProps.day === "numeric" || standardDateProps.day === "2-digit")) {
        biggestUnitForPartial = 1;
      }
      let full0 = this.format(start, context);
      let full1 = this.format(end, context);
      if (full0 === full1) {
        return full0;
      }
      let partialDateProps = computePartialFormattingOptions(standardDateProps, biggestUnitForPartial);
      let partialFormattingFunc = buildFormattingFunc(partialDateProps, extendedSettings, context);
      let partial0 = partialFormattingFunc(start);
      let partial1 = partialFormattingFunc(end);
      let insertion = findCommonInsertion(full0, partial0, full1, partial1);
      let separator = extendedSettings.separator || betterDefaultSeparator || context.defaultSeparator || "";
      if (insertion) {
        return insertion.before + partial0 + separator + partial1 + insertion.after;
      }
      return full0 + separator + full1;
    }
    getSmallestUnit() {
      switch (this.smallestUnitNum) {
        case 7:
        case 6:
        case 5:
          return "year";
        case 4:
          return "month";
        case 3:
          return "week";
        case 2:
          return "day";
        default:
          return "time";
      }
    }
  };
  function buildFormattingFunc(standardDateProps, extendedSettings, context) {
    let standardDatePropCnt = Object.keys(standardDateProps).length;
    if (standardDatePropCnt === 1 && standardDateProps.timeZoneName === "short") {
      return (date) => formatTimeZoneOffset(date.timeZoneOffset);
    }
    if (standardDatePropCnt === 0 && extendedSettings.week) {
      return (date) => formatWeekNumber(context.computeWeekNumber(date.marker), context.weekText, context.weekTextLong, context.locale, extendedSettings.week);
    }
    return buildNativeFormattingFunc(standardDateProps, extendedSettings, context);
  }
  function buildNativeFormattingFunc(standardDateProps, extendedSettings, context) {
    standardDateProps = Object.assign({}, standardDateProps);
    extendedSettings = Object.assign({}, extendedSettings);
    sanitizeSettings(standardDateProps, extendedSettings);
    standardDateProps.timeZone = "UTC";
    let normalFormat = new Intl.DateTimeFormat(context.locale.codes, standardDateProps);
    let zeroFormat;
    if (extendedSettings.omitZeroMinute) {
      let zeroProps = Object.assign({}, standardDateProps);
      delete zeroProps.minute;
      zeroFormat = new Intl.DateTimeFormat(context.locale.codes, zeroProps);
    }
    return (date) => {
      let { marker } = date;
      let format;
      if (zeroFormat && !marker.getUTCMinutes()) {
        format = zeroFormat;
      } else {
        format = normalFormat;
      }
      let s3 = format.format(marker);
      return postProcess(s3, date, standardDateProps, extendedSettings, context);
    };
  }
  function sanitizeSettings(standardDateProps, extendedSettings) {
    if (standardDateProps.timeZoneName) {
      if (!standardDateProps.hour) {
        standardDateProps.hour = "2-digit";
      }
      if (!standardDateProps.minute) {
        standardDateProps.minute = "2-digit";
      }
    }
    if (standardDateProps.timeZoneName === "long") {
      standardDateProps.timeZoneName = "short";
    }
    if (extendedSettings.omitZeroMinute && (standardDateProps.second || standardDateProps.millisecond)) {
      delete extendedSettings.omitZeroMinute;
    }
  }
  function postProcess(s3, date, standardDateProps, extendedSettings, context) {
    s3 = s3.replace(LTR_RE, "");
    if (standardDateProps.timeZoneName === "short") {
      s3 = injectTzoStr(s3, context.timeZone === "UTC" || date.timeZoneOffset == null ? "UTC" : formatTimeZoneOffset(date.timeZoneOffset));
    }
    if (extendedSettings.omitCommas) {
      s3 = s3.replace(COMMA_RE, "").trim();
    }
    if (extendedSettings.omitZeroMinute) {
      s3 = s3.replace(":00", "");
    }
    if (extendedSettings.meridiem === false) {
      s3 = s3.replace(MERIDIEM_RE, "").trim();
    } else if (extendedSettings.meridiem === "narrow") {
      s3 = s3.replace(MERIDIEM_RE, (m0, m1) => m1.toLocaleLowerCase());
    } else if (extendedSettings.meridiem === "short") {
      s3 = s3.replace(MERIDIEM_RE, (m0, m1) => `${m1.toLocaleLowerCase()}m`);
    } else if (extendedSettings.meridiem === "lowercase") {
      s3 = s3.replace(MERIDIEM_RE, (m0) => m0.toLocaleLowerCase());
    }
    s3 = s3.replace(MULTI_SPACE_RE, " ");
    s3 = s3.trim();
    return s3;
  }
  function injectTzoStr(s3, tzoStr) {
    let replaced = false;
    s3 = s3.replace(UTC_RE, () => {
      replaced = true;
      return tzoStr;
    });
    if (!replaced) {
      s3 += ` ${tzoStr}`;
    }
    return s3;
  }
  function formatWeekNumber(num, weekText, weekTextLong, locale, display) {
    let parts = [];
    if (display === "long") {
      parts.push(weekTextLong);
    } else if (display === "short" || display === "narrow") {
      parts.push(weekText);
    }
    if (display === "long" || display === "short") {
      parts.push(" ");
    }
    parts.push(locale.simpleNumberFormat.format(num));
    if (locale.options.direction === "rtl") {
      parts.reverse();
    }
    return parts.join("");
  }
  function computeMarkerDiffSeverity(d0, d1, ca) {
    if (ca.getMarkerYear(d0) !== ca.getMarkerYear(d1)) {
      return 5;
    }
    if (ca.getMarkerMonth(d0) !== ca.getMarkerMonth(d1)) {
      return 4;
    }
    if (ca.getMarkerDay(d0) !== ca.getMarkerDay(d1)) {
      return 2;
    }
    if (timeAsMs(d0) !== timeAsMs(d1)) {
      return 1;
    }
    return 0;
  }
  function computePartialFormattingOptions(options, biggestUnit) {
    let partialOptions = {};
    for (let name in options) {
      if (!(name in STANDARD_DATE_PROP_SEVERITIES) || STANDARD_DATE_PROP_SEVERITIES[name] <= biggestUnit) {
        partialOptions[name] = options[name];
      }
    }
    return partialOptions;
  }
  function findCommonInsertion(full0, partial0, full1, partial1) {
    let i0 = 0;
    while (i0 < full0.length) {
      let found0 = full0.indexOf(partial0, i0);
      if (found0 === -1) {
        break;
      }
      let before0 = full0.substr(0, found0);
      i0 = found0 + partial0.length;
      let after0 = full0.substr(i0);
      let i1 = 0;
      while (i1 < full1.length) {
        let found1 = full1.indexOf(partial1, i1);
        if (found1 === -1) {
          break;
        }
        let before1 = full1.substr(0, found1);
        i1 = found1 + partial1.length;
        let after1 = full1.substr(i1);
        if (before0 === before1 && after0 === after1) {
          return {
            before: before0,
            after: after0
          };
        }
      }
    }
    return null;
  }
  function expandZonedMarker(dateInfo, calendarSystem) {
    let a3 = calendarSystem.markerToArray(dateInfo.marker);
    return {
      marker: dateInfo.marker,
      timeZoneOffset: dateInfo.timeZoneOffset,
      array: a3,
      year: a3[0],
      month: a3[1],
      day: a3[2],
      hour: a3[3],
      minute: a3[4],
      second: a3[5],
      millisecond: a3[6]
    };
  }
  function createVerboseFormattingArg(start, end, context, betterDefaultSeparator) {
    let startInfo = expandZonedMarker(start, context.calendarSystem);
    let endInfo = end ? expandZonedMarker(end, context.calendarSystem) : null;
    return {
      date: startInfo,
      start: startInfo,
      end: endInfo,
      timeZone: context.timeZone,
      localeCodes: context.locale.codes,
      defaultSeparator: betterDefaultSeparator || context.defaultSeparator
    };
  }
  var CmdFormatter = class {
    constructor(cmdStr) {
      this.cmdStr = cmdStr;
    }
    format(date, context, betterDefaultSeparator) {
      return context.cmdFormatter(this.cmdStr, createVerboseFormattingArg(date, null, context, betterDefaultSeparator));
    }
    formatRange(start, end, context, betterDefaultSeparator) {
      return context.cmdFormatter(this.cmdStr, createVerboseFormattingArg(start, end, context, betterDefaultSeparator));
    }
  };
  var FuncFormatter = class {
    constructor(func) {
      this.func = func;
    }
    format(date, context, betterDefaultSeparator) {
      return this.func(createVerboseFormattingArg(date, null, context, betterDefaultSeparator));
    }
    formatRange(start, end, context, betterDefaultSeparator) {
      return this.func(createVerboseFormattingArg(start, end, context, betterDefaultSeparator));
    }
  };
  function createFormatter(input) {
    if (typeof input === "object" && input) {
      return new NativeFormatter(input);
    }
    if (typeof input === "string") {
      return new CmdFormatter(input);
    }
    if (typeof input === "function") {
      return new FuncFormatter(input);
    }
    return null;
  }
  var BASE_OPTION_REFINERS = {
    navLinkDayClick: identity,
    navLinkWeekClick: identity,
    duration: createDuration,
    bootstrapFontAwesome: identity,
    buttonIcons: identity,
    customButtons: identity,
    defaultAllDayEventDuration: createDuration,
    defaultTimedEventDuration: createDuration,
    nextDayThreshold: createDuration,
    scrollTime: createDuration,
    scrollTimeReset: Boolean,
    slotMinTime: createDuration,
    slotMaxTime: createDuration,
    dayPopoverFormat: createFormatter,
    slotDuration: createDuration,
    snapDuration: createDuration,
    headerToolbar: identity,
    footerToolbar: identity,
    defaultRangeSeparator: String,
    titleRangeSeparator: String,
    forceEventDuration: Boolean,
    dayHeaders: Boolean,
    dayHeaderFormat: createFormatter,
    dayHeaderClassNames: identity,
    dayHeaderContent: identity,
    dayHeaderDidMount: identity,
    dayHeaderWillUnmount: identity,
    dayCellClassNames: identity,
    dayCellContent: identity,
    dayCellDidMount: identity,
    dayCellWillUnmount: identity,
    initialView: String,
    aspectRatio: Number,
    weekends: Boolean,
    weekNumberCalculation: identity,
    weekNumbers: Boolean,
    weekNumberClassNames: identity,
    weekNumberContent: identity,
    weekNumberDidMount: identity,
    weekNumberWillUnmount: identity,
    editable: Boolean,
    viewClassNames: identity,
    viewDidMount: identity,
    viewWillUnmount: identity,
    nowIndicator: Boolean,
    nowIndicatorClassNames: identity,
    nowIndicatorContent: identity,
    nowIndicatorDidMount: identity,
    nowIndicatorWillUnmount: identity,
    showNonCurrentDates: Boolean,
    lazyFetching: Boolean,
    startParam: String,
    endParam: String,
    timeZoneParam: String,
    timeZone: String,
    locales: identity,
    locale: identity,
    themeSystem: String,
    dragRevertDuration: Number,
    dragScroll: Boolean,
    allDayMaintainDuration: Boolean,
    unselectAuto: Boolean,
    dropAccept: identity,
    eventOrder: parseFieldSpecs,
    eventOrderStrict: Boolean,
    handleWindowResize: Boolean,
    windowResizeDelay: Number,
    longPressDelay: Number,
    eventDragMinDistance: Number,
    expandRows: Boolean,
    height: identity,
    contentHeight: identity,
    direction: String,
    weekNumberFormat: createFormatter,
    eventResizableFromStart: Boolean,
    displayEventTime: Boolean,
    displayEventEnd: Boolean,
    weekText: String,
    weekTextLong: String,
    progressiveEventRendering: Boolean,
    businessHours: identity,
    initialDate: identity,
    now: identity,
    eventDataTransform: identity,
    stickyHeaderDates: identity,
    stickyFooterScrollbar: identity,
    viewHeight: identity,
    defaultAllDay: Boolean,
    eventSourceFailure: identity,
    eventSourceSuccess: identity,
    eventDisplay: String,
    eventStartEditable: Boolean,
    eventDurationEditable: Boolean,
    eventOverlap: identity,
    eventConstraint: identity,
    eventAllow: identity,
    eventBackgroundColor: String,
    eventBorderColor: String,
    eventTextColor: String,
    eventColor: String,
    eventClassNames: identity,
    eventContent: identity,
    eventDidMount: identity,
    eventWillUnmount: identity,
    selectConstraint: identity,
    selectOverlap: identity,
    selectAllow: identity,
    droppable: Boolean,
    unselectCancel: String,
    slotLabelFormat: identity,
    slotLaneClassNames: identity,
    slotLaneContent: identity,
    slotLaneDidMount: identity,
    slotLaneWillUnmount: identity,
    slotLabelClassNames: identity,
    slotLabelContent: identity,
    slotLabelDidMount: identity,
    slotLabelWillUnmount: identity,
    dayMaxEvents: identity,
    dayMaxEventRows: identity,
    dayMinWidth: Number,
    slotLabelInterval: createDuration,
    allDayText: String,
    allDayClassNames: identity,
    allDayContent: identity,
    allDayDidMount: identity,
    allDayWillUnmount: identity,
    slotMinWidth: Number,
    navLinks: Boolean,
    eventTimeFormat: createFormatter,
    rerenderDelay: Number,
    moreLinkText: identity,
    moreLinkHint: identity,
    selectMinDistance: Number,
    selectable: Boolean,
    selectLongPressDelay: Number,
    eventLongPressDelay: Number,
    selectMirror: Boolean,
    eventMaxStack: Number,
    eventMinHeight: Number,
    eventMinWidth: Number,
    eventShortHeight: Number,
    slotEventOverlap: Boolean,
    plugins: identity,
    firstDay: Number,
    dayCount: Number,
    dateAlignment: String,
    dateIncrement: createDuration,
    hiddenDays: identity,
    fixedWeekCount: Boolean,
    validRange: identity,
    visibleRange: identity,
    titleFormat: identity,
    eventInteractive: Boolean,
    noEventsText: String,
    viewHint: identity,
    navLinkHint: identity,
    closeHint: String,
    timeHint: String,
    eventHint: String,
    moreLinkClick: identity,
    moreLinkClassNames: identity,
    moreLinkContent: identity,
    moreLinkDidMount: identity,
    moreLinkWillUnmount: identity,
    monthStartFormat: createFormatter,
    handleCustomRendering: identity,
    customRenderingMetaMap: identity,
    customRenderingReplaces: Boolean
  };
  var BASE_OPTION_DEFAULTS = {
    eventDisplay: "auto",
    defaultRangeSeparator: " - ",
    titleRangeSeparator: " \u2013 ",
    defaultTimedEventDuration: "01:00:00",
    defaultAllDayEventDuration: { day: 1 },
    forceEventDuration: false,
    nextDayThreshold: "00:00:00",
    dayHeaders: true,
    initialView: "",
    aspectRatio: 1.35,
    headerToolbar: {
      start: "title",
      center: "",
      end: "today prev,next"
    },
    weekends: true,
    weekNumbers: false,
    weekNumberCalculation: "local",
    editable: false,
    nowIndicator: false,
    scrollTime: "06:00:00",
    scrollTimeReset: true,
    slotMinTime: "00:00:00",
    slotMaxTime: "24:00:00",
    showNonCurrentDates: true,
    lazyFetching: true,
    startParam: "start",
    endParam: "end",
    timeZoneParam: "timeZone",
    timeZone: "local",
    locales: [],
    locale: "",
    themeSystem: "standard",
    dragRevertDuration: 500,
    dragScroll: true,
    allDayMaintainDuration: false,
    unselectAuto: true,
    dropAccept: "*",
    eventOrder: "start,-duration,allDay,title",
    dayPopoverFormat: { month: "long", day: "numeric", year: "numeric" },
    handleWindowResize: true,
    windowResizeDelay: 100,
    longPressDelay: 1e3,
    eventDragMinDistance: 5,
    expandRows: false,
    navLinks: false,
    selectable: false,
    eventMinHeight: 15,
    eventMinWidth: 30,
    eventShortHeight: 30,
    monthStartFormat: { month: "long", day: "numeric" }
  };
  var CALENDAR_LISTENER_REFINERS = {
    datesSet: identity,
    eventsSet: identity,
    eventAdd: identity,
    eventChange: identity,
    eventRemove: identity,
    windowResize: identity,
    eventClick: identity,
    eventMouseEnter: identity,
    eventMouseLeave: identity,
    select: identity,
    unselect: identity,
    loading: identity,
    _unmount: identity,
    _beforeprint: identity,
    _afterprint: identity,
    _noEventDrop: identity,
    _noEventResize: identity,
    _resize: identity,
    _scrollRequest: identity
  };
  var CALENDAR_OPTION_REFINERS = {
    buttonText: identity,
    buttonHints: identity,
    views: identity,
    plugins: identity,
    initialEvents: identity,
    events: identity,
    eventSources: identity
  };
  var COMPLEX_OPTION_COMPARATORS = {
    headerToolbar: isMaybeObjectsEqual,
    footerToolbar: isMaybeObjectsEqual,
    buttonText: isMaybeObjectsEqual,
    buttonHints: isMaybeObjectsEqual,
    buttonIcons: isMaybeObjectsEqual,
    dateIncrement: isMaybeObjectsEqual,
    plugins: isMaybeArraysEqual,
    events: isMaybeArraysEqual,
    eventSources: isMaybeArraysEqual,
    ["resources"]: isMaybeArraysEqual
  };
  function isMaybeObjectsEqual(a3, b3) {
    if (typeof a3 === "object" && typeof b3 === "object" && a3 && b3) {
      return isPropsEqual(a3, b3);
    }
    return a3 === b3;
  }
  function isMaybeArraysEqual(a3, b3) {
    if (Array.isArray(a3) && Array.isArray(b3)) {
      return isArraysEqual(a3, b3);
    }
    return a3 === b3;
  }
  var VIEW_OPTION_REFINERS = {
    type: String,
    component: identity,
    buttonText: String,
    buttonTextKey: String,
    dateProfileGeneratorClass: identity,
    usesMinMaxTime: Boolean,
    classNames: identity,
    content: identity,
    didMount: identity,
    willUnmount: identity
  };
  function mergeRawOptions(optionSets) {
    return mergeProps(optionSets, COMPLEX_OPTION_COMPARATORS);
  }
  function refineProps(input, refiners) {
    let refined = {};
    let extra = {};
    for (let propName in refiners) {
      if (propName in input) {
        refined[propName] = refiners[propName](input[propName]);
      }
    }
    for (let propName in input) {
      if (!(propName in refiners)) {
        extra[propName] = input[propName];
      }
    }
    return { refined, extra };
  }
  function identity(raw) {
    return raw;
  }
  var { hasOwnProperty } = Object.prototype;
  function mergeProps(propObjs, complexPropsMap) {
    let dest = {};
    if (complexPropsMap) {
      for (let name in complexPropsMap) {
        if (complexPropsMap[name] === isMaybeObjectsEqual) {
          let complexObjs = [];
          for (let i3 = propObjs.length - 1; i3 >= 0; i3 -= 1) {
            let val = propObjs[i3][name];
            if (typeof val === "object" && val) {
              complexObjs.unshift(val);
            } else if (val !== void 0) {
              dest[name] = val;
              break;
            }
          }
          if (complexObjs.length) {
            dest[name] = mergeProps(complexObjs);
          }
        }
      }
    }
    for (let i3 = propObjs.length - 1; i3 >= 0; i3 -= 1) {
      let props = propObjs[i3];
      for (let name in props) {
        if (!(name in dest)) {
          dest[name] = props[name];
        }
      }
    }
    return dest;
  }
  function filterHash(hash, func) {
    let filtered = {};
    for (let key in hash) {
      if (func(hash[key], key)) {
        filtered[key] = hash[key];
      }
    }
    return filtered;
  }
  function mapHash(hash, func) {
    let newHash = {};
    for (let key in hash) {
      newHash[key] = func(hash[key], key);
    }
    return newHash;
  }
  function arrayToHash(a3) {
    let hash = {};
    for (let item of a3) {
      hash[item] = true;
    }
    return hash;
  }
  function hashValuesToArray(obj) {
    let a3 = [];
    for (let key in obj) {
      a3.push(obj[key]);
    }
    return a3;
  }
  function isPropsEqual(obj0, obj1) {
    if (obj0 === obj1) {
      return true;
    }
    for (let key in obj0) {
      if (hasOwnProperty.call(obj0, key)) {
        if (!(key in obj1)) {
          return false;
        }
      }
    }
    for (let key in obj1) {
      if (hasOwnProperty.call(obj1, key)) {
        if (obj0[key] !== obj1[key]) {
          return false;
        }
      }
    }
    return true;
  }
  var HANDLER_RE = /^on[A-Z]/;
  function isNonHandlerPropsEqual(obj0, obj1) {
    const keys = getUnequalProps(obj0, obj1);
    for (let key of keys) {
      if (!HANDLER_RE.test(key)) {
        return false;
      }
    }
    return true;
  }
  function getUnequalProps(obj0, obj1) {
    let keys = [];
    for (let key in obj0) {
      if (hasOwnProperty.call(obj0, key)) {
        if (!(key in obj1)) {
          keys.push(key);
        }
      }
    }
    for (let key in obj1) {
      if (hasOwnProperty.call(obj1, key)) {
        if (obj0[key] !== obj1[key]) {
          keys.push(key);
        }
      }
    }
    return keys;
  }
  function compareObjs(oldProps, newProps, equalityFuncs = {}) {
    if (oldProps === newProps) {
      return true;
    }
    for (let key in newProps) {
      if (key in oldProps && isObjValsEqual(oldProps[key], newProps[key], equalityFuncs[key]))
        ;
      else {
        return false;
      }
    }
    for (let key in oldProps) {
      if (!(key in newProps)) {
        return false;
      }
    }
    return true;
  }
  function isObjValsEqual(val0, val1, comparator) {
    if (val0 === val1 || comparator === true) {
      return true;
    }
    if (comparator) {
      return comparator(val0, val1);
    }
    return false;
  }
  function collectFromHash(hash, startIndex = 0, endIndex, step = 1) {
    let res = [];
    if (endIndex == null) {
      endIndex = Object.keys(hash).length;
    }
    for (let i3 = startIndex; i3 < endIndex; i3 += step) {
      let val = hash[i3];
      if (val !== void 0) {
        res.push(val);
      }
    }
    return res;
  }
  var calendarSystemClassMap = {};
  function registerCalendarSystem(name, theClass) {
    calendarSystemClassMap[name] = theClass;
  }
  function createCalendarSystem(name) {
    return new calendarSystemClassMap[name]();
  }
  var GregorianCalendarSystem = class {
    getMarkerYear(d2) {
      return d2.getUTCFullYear();
    }
    getMarkerMonth(d2) {
      return d2.getUTCMonth();
    }
    getMarkerDay(d2) {
      return d2.getUTCDate();
    }
    arrayToMarker(arr) {
      return arrayToUtcDate(arr);
    }
    markerToArray(marker) {
      return dateToUtcArray(marker);
    }
  };
  registerCalendarSystem("gregory", GregorianCalendarSystem);
  var ISO_RE = /^\s*(\d{4})(-?(\d{2})(-?(\d{2})([T ](\d{2}):?(\d{2})(:?(\d{2})(\.(\d+))?)?(Z|(([-+])(\d{2})(:?(\d{2}))?))?)?)?)?$/;
  function parse(str) {
    let m3 = ISO_RE.exec(str);
    if (m3) {
      let marker = new Date(Date.UTC(Number(m3[1]), m3[3] ? Number(m3[3]) - 1 : 0, Number(m3[5] || 1), Number(m3[7] || 0), Number(m3[8] || 0), Number(m3[10] || 0), m3[12] ? Number(`0.${m3[12]}`) * 1e3 : 0));
      if (isValidDate(marker)) {
        let timeZoneOffset = null;
        if (m3[13]) {
          timeZoneOffset = (m3[15] === "-" ? -1 : 1) * (Number(m3[16] || 0) * 60 + Number(m3[18] || 0));
        }
        return {
          marker,
          isTimeUnspecified: !m3[6],
          timeZoneOffset
        };
      }
    }
    return null;
  }
  var DateEnv = class {
    constructor(settings) {
      let timeZone = this.timeZone = settings.timeZone;
      let isNamedTimeZone = timeZone !== "local" && timeZone !== "UTC";
      if (settings.namedTimeZoneImpl && isNamedTimeZone) {
        this.namedTimeZoneImpl = new settings.namedTimeZoneImpl(timeZone);
      }
      this.canComputeOffset = Boolean(!isNamedTimeZone || this.namedTimeZoneImpl);
      this.calendarSystem = createCalendarSystem(settings.calendarSystem);
      this.locale = settings.locale;
      this.weekDow = settings.locale.week.dow;
      this.weekDoy = settings.locale.week.doy;
      if (settings.weekNumberCalculation === "ISO") {
        this.weekDow = 1;
        this.weekDoy = 4;
      }
      if (typeof settings.firstDay === "number") {
        this.weekDow = settings.firstDay;
      }
      if (typeof settings.weekNumberCalculation === "function") {
        this.weekNumberFunc = settings.weekNumberCalculation;
      }
      this.weekText = settings.weekText != null ? settings.weekText : settings.locale.options.weekText;
      this.weekTextLong = (settings.weekTextLong != null ? settings.weekTextLong : settings.locale.options.weekTextLong) || this.weekText;
      this.cmdFormatter = settings.cmdFormatter;
      this.defaultSeparator = settings.defaultSeparator;
    }
    createMarker(input) {
      let meta = this.createMarkerMeta(input);
      if (meta === null) {
        return null;
      }
      return meta.marker;
    }
    createNowMarker() {
      if (this.canComputeOffset) {
        return this.timestampToMarker(new Date().valueOf());
      }
      return arrayToUtcDate(dateToLocalArray(new Date()));
    }
    createMarkerMeta(input) {
      if (typeof input === "string") {
        return this.parse(input);
      }
      let marker = null;
      if (typeof input === "number") {
        marker = this.timestampToMarker(input);
      } else if (input instanceof Date) {
        input = input.valueOf();
        if (!isNaN(input)) {
          marker = this.timestampToMarker(input);
        }
      } else if (Array.isArray(input)) {
        marker = arrayToUtcDate(input);
      }
      if (marker === null || !isValidDate(marker)) {
        return null;
      }
      return { marker, isTimeUnspecified: false, forcedTzo: null };
    }
    parse(s3) {
      let parts = parse(s3);
      if (parts === null) {
        return null;
      }
      let { marker } = parts;
      let forcedTzo = null;
      if (parts.timeZoneOffset !== null) {
        if (this.canComputeOffset) {
          marker = this.timestampToMarker(marker.valueOf() - parts.timeZoneOffset * 60 * 1e3);
        } else {
          forcedTzo = parts.timeZoneOffset;
        }
      }
      return { marker, isTimeUnspecified: parts.isTimeUnspecified, forcedTzo };
    }
    getYear(marker) {
      return this.calendarSystem.getMarkerYear(marker);
    }
    getMonth(marker) {
      return this.calendarSystem.getMarkerMonth(marker);
    }
    getDay(marker) {
      return this.calendarSystem.getMarkerDay(marker);
    }
    add(marker, dur) {
      let a3 = this.calendarSystem.markerToArray(marker);
      a3[0] += dur.years;
      a3[1] += dur.months;
      a3[2] += dur.days;
      a3[6] += dur.milliseconds;
      return this.calendarSystem.arrayToMarker(a3);
    }
    subtract(marker, dur) {
      let a3 = this.calendarSystem.markerToArray(marker);
      a3[0] -= dur.years;
      a3[1] -= dur.months;
      a3[2] -= dur.days;
      a3[6] -= dur.milliseconds;
      return this.calendarSystem.arrayToMarker(a3);
    }
    addYears(marker, n2) {
      let a3 = this.calendarSystem.markerToArray(marker);
      a3[0] += n2;
      return this.calendarSystem.arrayToMarker(a3);
    }
    addMonths(marker, n2) {
      let a3 = this.calendarSystem.markerToArray(marker);
      a3[1] += n2;
      return this.calendarSystem.arrayToMarker(a3);
    }
    diffWholeYears(m0, m1) {
      let { calendarSystem } = this;
      if (timeAsMs(m0) === timeAsMs(m1) && calendarSystem.getMarkerDay(m0) === calendarSystem.getMarkerDay(m1) && calendarSystem.getMarkerMonth(m0) === calendarSystem.getMarkerMonth(m1)) {
        return calendarSystem.getMarkerYear(m1) - calendarSystem.getMarkerYear(m0);
      }
      return null;
    }
    diffWholeMonths(m0, m1) {
      let { calendarSystem } = this;
      if (timeAsMs(m0) === timeAsMs(m1) && calendarSystem.getMarkerDay(m0) === calendarSystem.getMarkerDay(m1)) {
        return calendarSystem.getMarkerMonth(m1) - calendarSystem.getMarkerMonth(m0) + (calendarSystem.getMarkerYear(m1) - calendarSystem.getMarkerYear(m0)) * 12;
      }
      return null;
    }
    greatestWholeUnit(m0, m1) {
      let n2 = this.diffWholeYears(m0, m1);
      if (n2 !== null) {
        return { unit: "year", value: n2 };
      }
      n2 = this.diffWholeMonths(m0, m1);
      if (n2 !== null) {
        return { unit: "month", value: n2 };
      }
      n2 = diffWholeWeeks(m0, m1);
      if (n2 !== null) {
        return { unit: "week", value: n2 };
      }
      n2 = diffWholeDays(m0, m1);
      if (n2 !== null) {
        return { unit: "day", value: n2 };
      }
      n2 = diffHours(m0, m1);
      if (isInt(n2)) {
        return { unit: "hour", value: n2 };
      }
      n2 = diffMinutes(m0, m1);
      if (isInt(n2)) {
        return { unit: "minute", value: n2 };
      }
      n2 = diffSeconds(m0, m1);
      if (isInt(n2)) {
        return { unit: "second", value: n2 };
      }
      return { unit: "millisecond", value: m1.valueOf() - m0.valueOf() };
    }
    countDurationsBetween(m0, m1, d2) {
      let diff;
      if (d2.years) {
        diff = this.diffWholeYears(m0, m1);
        if (diff !== null) {
          return diff / asRoughYears(d2);
        }
      }
      if (d2.months) {
        diff = this.diffWholeMonths(m0, m1);
        if (diff !== null) {
          return diff / asRoughMonths(d2);
        }
      }
      if (d2.days) {
        diff = diffWholeDays(m0, m1);
        if (diff !== null) {
          return diff / asRoughDays(d2);
        }
      }
      return (m1.valueOf() - m0.valueOf()) / asRoughMs(d2);
    }
    startOf(m3, unit) {
      if (unit === "year") {
        return this.startOfYear(m3);
      }
      if (unit === "month") {
        return this.startOfMonth(m3);
      }
      if (unit === "week") {
        return this.startOfWeek(m3);
      }
      if (unit === "day") {
        return startOfDay(m3);
      }
      if (unit === "hour") {
        return startOfHour(m3);
      }
      if (unit === "minute") {
        return startOfMinute(m3);
      }
      if (unit === "second") {
        return startOfSecond(m3);
      }
      return null;
    }
    startOfYear(m3) {
      return this.calendarSystem.arrayToMarker([
        this.calendarSystem.getMarkerYear(m3)
      ]);
    }
    startOfMonth(m3) {
      return this.calendarSystem.arrayToMarker([
        this.calendarSystem.getMarkerYear(m3),
        this.calendarSystem.getMarkerMonth(m3)
      ]);
    }
    startOfWeek(m3) {
      return this.calendarSystem.arrayToMarker([
        this.calendarSystem.getMarkerYear(m3),
        this.calendarSystem.getMarkerMonth(m3),
        m3.getUTCDate() - (m3.getUTCDay() - this.weekDow + 7) % 7
      ]);
    }
    computeWeekNumber(marker) {
      if (this.weekNumberFunc) {
        return this.weekNumberFunc(this.toDate(marker));
      }
      return weekOfYear(marker, this.weekDow, this.weekDoy);
    }
    format(marker, formatter, dateOptions = {}) {
      return formatter.format({
        marker,
        timeZoneOffset: dateOptions.forcedTzo != null ? dateOptions.forcedTzo : this.offsetForMarker(marker)
      }, this);
    }
    formatRange(start, end, formatter, dateOptions = {}) {
      if (dateOptions.isEndExclusive) {
        end = addMs(end, -1);
      }
      return formatter.formatRange({
        marker: start,
        timeZoneOffset: dateOptions.forcedStartTzo != null ? dateOptions.forcedStartTzo : this.offsetForMarker(start)
      }, {
        marker: end,
        timeZoneOffset: dateOptions.forcedEndTzo != null ? dateOptions.forcedEndTzo : this.offsetForMarker(end)
      }, this, dateOptions.defaultSeparator);
    }
    formatIso(marker, extraOptions = {}) {
      let timeZoneOffset = null;
      if (!extraOptions.omitTimeZoneOffset) {
        if (extraOptions.forcedTzo != null) {
          timeZoneOffset = extraOptions.forcedTzo;
        } else {
          timeZoneOffset = this.offsetForMarker(marker);
        }
      }
      return buildIsoString(marker, timeZoneOffset, extraOptions.omitTime);
    }
    timestampToMarker(ms) {
      if (this.timeZone === "local") {
        return arrayToUtcDate(dateToLocalArray(new Date(ms)));
      }
      if (this.timeZone === "UTC" || !this.namedTimeZoneImpl) {
        return new Date(ms);
      }
      return arrayToUtcDate(this.namedTimeZoneImpl.timestampToArray(ms));
    }
    offsetForMarker(m3) {
      if (this.timeZone === "local") {
        return -arrayToLocalDate(dateToUtcArray(m3)).getTimezoneOffset();
      }
      if (this.timeZone === "UTC") {
        return 0;
      }
      if (this.namedTimeZoneImpl) {
        return this.namedTimeZoneImpl.offsetForArray(dateToUtcArray(m3));
      }
      return null;
    }
    toDate(m3, forcedTzo) {
      if (this.timeZone === "local") {
        return arrayToLocalDate(dateToUtcArray(m3));
      }
      if (this.timeZone === "UTC") {
        return new Date(m3.valueOf());
      }
      if (!this.namedTimeZoneImpl) {
        return new Date(m3.valueOf() - (forcedTzo || 0));
      }
      return new Date(m3.valueOf() - this.namedTimeZoneImpl.offsetForArray(dateToUtcArray(m3)) * 1e3 * 60);
    }
  };
  var Theme = class {
    constructor(calendarOptions) {
      if (this.iconOverrideOption) {
        this.setIconOverride(calendarOptions[this.iconOverrideOption]);
      }
    }
    setIconOverride(iconOverrideHash) {
      let iconClassesCopy;
      let buttonName;
      if (typeof iconOverrideHash === "object" && iconOverrideHash) {
        iconClassesCopy = Object.assign({}, this.iconClasses);
        for (buttonName in iconOverrideHash) {
          iconClassesCopy[buttonName] = this.applyIconOverridePrefix(iconOverrideHash[buttonName]);
        }
        this.iconClasses = iconClassesCopy;
      } else if (iconOverrideHash === false) {
        this.iconClasses = {};
      }
    }
    applyIconOverridePrefix(className) {
      let prefix = this.iconOverridePrefix;
      if (prefix && className.indexOf(prefix) !== 0) {
        className = prefix + className;
      }
      return className;
    }
    getClass(key) {
      return this.classes[key] || "";
    }
    getIconClass(buttonName, isRtl) {
      let className;
      if (isRtl && this.rtlIconClasses) {
        className = this.rtlIconClasses[buttonName] || this.iconClasses[buttonName];
      } else {
        className = this.iconClasses[buttonName];
      }
      if (className) {
        return `${this.baseIconClass} ${className}`;
      }
      return "";
    }
    getCustomButtonIconClass(customButtonProps) {
      let className;
      if (this.iconOverrideCustomButtonOption) {
        className = customButtonProps[this.iconOverrideCustomButtonOption];
        if (className) {
          return `${this.baseIconClass} ${this.applyIconOverridePrefix(className)}`;
        }
      }
      return "";
    }
  };
  Theme.prototype.classes = {};
  Theme.prototype.iconClasses = {};
  Theme.prototype.baseIconClass = "";
  Theme.prototype.iconOverridePrefix = "";
  function flushSync(runBeforeFlush) {
    runBeforeFlush();
    let oldDebounceRendering = l.debounceRendering;
    let callbackQ = [];
    function execCallbackSync(callback) {
      callbackQ.push(callback);
    }
    l.debounceRendering = execCallbackSync;
    D(y(FakeComponent, {}), document.createElement("div"));
    while (callbackQ.length) {
      callbackQ.shift()();
    }
    l.debounceRendering = oldDebounceRendering;
  }
  var FakeComponent = class extends x {
    render() {
      return y("div", {});
    }
    componentDidMount() {
      this.setState({});
    }
  };
  function createContext(defaultValue) {
    let ContextType = G(defaultValue);
    let origProvider = ContextType.Provider;
    ContextType.Provider = function() {
      let isNew = !this.getChildContext;
      let children = origProvider.apply(this, arguments);
      if (isNew) {
        let subs = [];
        this.shouldComponentUpdate = (_props) => {
          if (this.props.value !== _props.value) {
            subs.forEach((c3) => {
              c3.context = _props.value;
              c3.forceUpdate();
            });
          }
        };
        this.sub = (c3) => {
          subs.push(c3);
          let old = c3.componentWillUnmount;
          c3.componentWillUnmount = () => {
            subs.splice(subs.indexOf(c3), 1);
            old && old.call(c3);
          };
        };
      }
      return children;
    };
    return ContextType;
  }
  var ScrollResponder = class {
    constructor(execFunc, emitter, scrollTime, scrollTimeReset) {
      this.execFunc = execFunc;
      this.emitter = emitter;
      this.scrollTime = scrollTime;
      this.scrollTimeReset = scrollTimeReset;
      this.handleScrollRequest = (request) => {
        this.queuedRequest = Object.assign({}, this.queuedRequest || {}, request);
        this.drain();
      };
      emitter.on("_scrollRequest", this.handleScrollRequest);
      this.fireInitialScroll();
    }
    detach() {
      this.emitter.off("_scrollRequest", this.handleScrollRequest);
    }
    update(isDatesNew) {
      if (isDatesNew && this.scrollTimeReset) {
        this.fireInitialScroll();
      } else {
        this.drain();
      }
    }
    fireInitialScroll() {
      this.handleScrollRequest({
        time: this.scrollTime
      });
    }
    drain() {
      if (this.queuedRequest && this.execFunc(this.queuedRequest)) {
        this.queuedRequest = null;
      }
    }
  };
  var ViewContextType = createContext({});
  function buildViewContext(viewSpec, viewApi, viewOptions, dateProfileGenerator, dateEnv, nowManager, theme, pluginHooks, dispatch, getCurrentData, emitter, calendarApi, registerInteractiveComponent, unregisterInteractiveComponent) {
    return {
      dateEnv,
      nowManager,
      options: viewOptions,
      pluginHooks,
      emitter,
      dispatch,
      getCurrentData,
      calendarApi,
      viewSpec,
      viewApi,
      dateProfileGenerator,
      theme,
      isRtl: viewOptions.direction === "rtl",
      addResizeHandler(handler) {
        emitter.on("_resize", handler);
      },
      removeResizeHandler(handler) {
        emitter.off("_resize", handler);
      },
      createScrollResponder(execFunc) {
        return new ScrollResponder(execFunc, emitter, createDuration(viewOptions.scrollTime), viewOptions.scrollTimeReset);
      },
      registerInteractiveComponent,
      unregisterInteractiveComponent
    };
  }
  var PureComponent = class extends x {
    shouldComponentUpdate(nextProps, nextState) {
      if (this.debug) {
        console.log(getUnequalProps(nextProps, this.props), getUnequalProps(nextState, this.state));
      }
      return !compareObjs(this.props, nextProps, this.propEquality) || !compareObjs(this.state, nextState, this.stateEquality);
    }
    safeSetState(newState) {
      if (!compareObjs(this.state, Object.assign(Object.assign({}, this.state), newState), this.stateEquality)) {
        this.setState(newState);
      }
    }
  };
  PureComponent.addPropsEquality = addPropsEquality;
  PureComponent.addStateEquality = addStateEquality;
  PureComponent.contextType = ViewContextType;
  PureComponent.prototype.propEquality = {};
  PureComponent.prototype.stateEquality = {};
  var BaseComponent = class extends PureComponent {
  };
  BaseComponent.contextType = ViewContextType;
  function addPropsEquality(propEquality) {
    let hash = Object.create(this.prototype.propEquality);
    Object.assign(hash, propEquality);
    this.prototype.propEquality = hash;
  }
  function addStateEquality(stateEquality) {
    let hash = Object.create(this.prototype.stateEquality);
    Object.assign(hash, stateEquality);
    this.prototype.stateEquality = hash;
  }
  function setRef(ref, current) {
    if (typeof ref === "function") {
      ref(current);
    } else if (ref) {
      ref.current = current;
    }
  }
  var ContentInjector = class extends BaseComponent {
    constructor() {
      super(...arguments);
      this.id = guid();
      this.queuedDomNodes = [];
      this.currentDomNodes = [];
      this.handleEl = (el) => {
        const { options } = this.context;
        const { generatorName } = this.props;
        if (!options.customRenderingReplaces || !hasCustomRenderingHandler(generatorName, options)) {
          this.updateElRef(el);
        }
      };
      this.updateElRef = (el) => {
        if (this.props.elRef) {
          setRef(this.props.elRef, el);
        }
      };
    }
    render() {
      const { props, context } = this;
      const { options } = context;
      const { customGenerator, defaultGenerator, renderProps } = props;
      const attrs = buildElAttrs(props, [], this.handleEl);
      let useDefault = false;
      let innerContent;
      let queuedDomNodes = [];
      let currentGeneratorMeta;
      if (customGenerator != null) {
        const customGeneratorRes = typeof customGenerator === "function" ? customGenerator(renderProps, y) : customGenerator;
        if (customGeneratorRes === true) {
          useDefault = true;
        } else {
          const isObject = customGeneratorRes && typeof customGeneratorRes === "object";
          if (isObject && "html" in customGeneratorRes) {
            attrs.dangerouslySetInnerHTML = { __html: customGeneratorRes.html };
          } else if (isObject && "domNodes" in customGeneratorRes) {
            queuedDomNodes = Array.prototype.slice.call(customGeneratorRes.domNodes);
          } else if (isObject ? i(customGeneratorRes) : typeof customGeneratorRes !== "function") {
            innerContent = customGeneratorRes;
          } else {
            currentGeneratorMeta = customGeneratorRes;
          }
        }
      } else {
        useDefault = !hasCustomRenderingHandler(props.generatorName, options);
      }
      if (useDefault && defaultGenerator) {
        innerContent = defaultGenerator(renderProps);
      }
      this.queuedDomNodes = queuedDomNodes;
      this.currentGeneratorMeta = currentGeneratorMeta;
      return y(props.elTag, attrs, innerContent);
    }
    componentDidMount() {
      this.applyQueueudDomNodes();
      this.triggerCustomRendering(true);
    }
    componentDidUpdate() {
      this.applyQueueudDomNodes();
      this.triggerCustomRendering(true);
    }
    componentWillUnmount() {
      this.triggerCustomRendering(false);
    }
    triggerCustomRendering(isActive) {
      var _a;
      const { props, context } = this;
      const { handleCustomRendering, customRenderingMetaMap } = context.options;
      if (handleCustomRendering) {
        const generatorMeta = (_a = this.currentGeneratorMeta) !== null && _a !== void 0 ? _a : customRenderingMetaMap === null || customRenderingMetaMap === void 0 ? void 0 : customRenderingMetaMap[props.generatorName];
        if (generatorMeta) {
          handleCustomRendering(Object.assign(Object.assign({
            id: this.id,
            isActive,
            containerEl: this.base,
            reportNewContainerEl: this.updateElRef,
            generatorMeta
          }, props), { elClasses: (props.elClasses || []).filter(isTruthy) }));
        }
      }
    }
    applyQueueudDomNodes() {
      const { queuedDomNodes, currentDomNodes } = this;
      const el = this.base;
      if (!isArraysEqual(queuedDomNodes, currentDomNodes)) {
        currentDomNodes.forEach(removeElement);
        for (let newNode of queuedDomNodes) {
          el.appendChild(newNode);
        }
        this.currentDomNodes = queuedDomNodes;
      }
    }
  };
  ContentInjector.addPropsEquality({
    elClasses: isArraysEqual,
    elStyle: isPropsEqual,
    elAttrs: isNonHandlerPropsEqual,
    renderProps: isPropsEqual
  });
  function hasCustomRenderingHandler(generatorName, options) {
    var _a;
    return Boolean(options.handleCustomRendering && generatorName && ((_a = options.customRenderingMetaMap) === null || _a === void 0 ? void 0 : _a[generatorName]));
  }
  function buildElAttrs(props, extraClassNames, elRef) {
    const attrs = Object.assign(Object.assign({}, props.elAttrs), { ref: elRef });
    if (props.elClasses || extraClassNames) {
      attrs.className = (props.elClasses || []).concat(extraClassNames || []).concat(attrs.className || []).filter(Boolean).join(" ");
    }
    if (props.elStyle) {
      attrs.style = props.elStyle;
    }
    return attrs;
  }
  function isTruthy(val) {
    return Boolean(val);
  }
  var RenderId = createContext(0);
  var ContentContainer = class extends x {
    constructor() {
      super(...arguments);
      this.InnerContent = InnerContentInjector.bind(void 0, this);
      this.handleEl = (el) => {
        this.el = el;
        if (this.props.elRef) {
          setRef(this.props.elRef, el);
          if (el && this.didMountMisfire) {
            this.componentDidMount();
          }
        }
      };
    }
    render() {
      const { props } = this;
      const generatedClassNames = generateClassNames(props.classNameGenerator, props.renderProps);
      if (props.children) {
        const elAttrs = buildElAttrs(props, generatedClassNames, this.handleEl);
        const children = props.children(this.InnerContent, props.renderProps, elAttrs);
        if (props.elTag) {
          return y(props.elTag, elAttrs, children);
        } else {
          return children;
        }
      } else {
        return y(ContentInjector, Object.assign(Object.assign({}, props), { elRef: this.handleEl, elTag: props.elTag || "div", elClasses: (props.elClasses || []).concat(generatedClassNames), renderId: this.context }));
      }
    }
    componentDidMount() {
      var _a, _b;
      if (this.el) {
        (_b = (_a = this.props).didMount) === null || _b === void 0 ? void 0 : _b.call(_a, Object.assign(Object.assign({}, this.props.renderProps), { el: this.el }));
      } else {
        this.didMountMisfire = true;
      }
    }
    componentWillUnmount() {
      var _a, _b;
      (_b = (_a = this.props).willUnmount) === null || _b === void 0 ? void 0 : _b.call(_a, Object.assign(Object.assign({}, this.props.renderProps), { el: this.el }));
    }
  };
  ContentContainer.contextType = RenderId;
  function InnerContentInjector(containerComponent, props) {
    const parentProps = containerComponent.props;
    return y(ContentInjector, Object.assign({ renderProps: parentProps.renderProps, generatorName: parentProps.generatorName, customGenerator: parentProps.customGenerator, defaultGenerator: parentProps.defaultGenerator, renderId: containerComponent.context }, props));
  }
  function generateClassNames(classNameGenerator, renderProps) {
    const classNames = typeof classNameGenerator === "function" ? classNameGenerator(renderProps) : classNameGenerator || [];
    return typeof classNames === "string" ? [classNames] : classNames;
  }
  var ViewContainer = class extends BaseComponent {
    render() {
      let { props, context } = this;
      let { options } = context;
      let renderProps = { view: context.viewApi };
      return y(ContentContainer, Object.assign({}, props, { elTag: props.elTag || "div", elClasses: [
        ...buildViewClassNames(props.viewSpec),
        ...props.elClasses || []
      ], renderProps, classNameGenerator: options.viewClassNames, generatorName: void 0, didMount: options.viewDidMount, willUnmount: options.viewWillUnmount }), () => props.children);
    }
  };
  function buildViewClassNames(viewSpec) {
    return [
      `fc-${viewSpec.type}-view`,
      "fc-view"
    ];
  }
  function parseRange(input, dateEnv) {
    let start = null;
    let end = null;
    if (input.start) {
      start = dateEnv.createMarker(input.start);
    }
    if (input.end) {
      end = dateEnv.createMarker(input.end);
    }
    if (!start && !end) {
      return null;
    }
    if (start && end && end < start) {
      return null;
    }
    return { start, end };
  }
  function invertRanges(ranges, constraintRange) {
    let invertedRanges = [];
    let { start } = constraintRange;
    let i3;
    let dateRange;
    ranges.sort(compareRanges);
    for (i3 = 0; i3 < ranges.length; i3 += 1) {
      dateRange = ranges[i3];
      if (dateRange.start > start) {
        invertedRanges.push({ start, end: dateRange.start });
      }
      if (dateRange.end > start) {
        start = dateRange.end;
      }
    }
    if (start < constraintRange.end) {
      invertedRanges.push({ start, end: constraintRange.end });
    }
    return invertedRanges;
  }
  function compareRanges(range0, range1) {
    return range0.start.valueOf() - range1.start.valueOf();
  }
  function intersectRanges(range0, range1) {
    let { start, end } = range0;
    let newRange = null;
    if (range1.start !== null) {
      if (start === null) {
        start = range1.start;
      } else {
        start = new Date(Math.max(start.valueOf(), range1.start.valueOf()));
      }
    }
    if (range1.end != null) {
      if (end === null) {
        end = range1.end;
      } else {
        end = new Date(Math.min(end.valueOf(), range1.end.valueOf()));
      }
    }
    if (start === null || end === null || start < end) {
      newRange = { start, end };
    }
    return newRange;
  }
  function rangesIntersect(range0, range1) {
    return (range0.end === null || range1.start === null || range0.end > range1.start) && (range0.start === null || range1.end === null || range0.start < range1.end);
  }
  function rangeContainsMarker(range, date) {
    return (range.start === null || date >= range.start) && (range.end === null || date < range.end);
  }
  function constrainMarkerToRange(date, range) {
    if (range.start != null && date < range.start) {
      return range.start;
    }
    if (range.end != null && date >= range.end) {
      return new Date(range.end.valueOf() - 1);
    }
    return date;
  }
  function computeAlignedDayRange(timedRange) {
    let dayCnt = Math.floor(diffDays(timedRange.start, timedRange.end)) || 1;
    let start = startOfDay(timedRange.start);
    let end = addDays(start, dayCnt);
    return { start, end };
  }
  function computeVisibleDayRange(timedRange, nextDayThreshold = createDuration(0)) {
    let startDay = null;
    let endDay = null;
    if (timedRange.end) {
      endDay = startOfDay(timedRange.end);
      let endTimeMS = timedRange.end.valueOf() - endDay.valueOf();
      if (endTimeMS && endTimeMS >= asRoughMs(nextDayThreshold)) {
        endDay = addDays(endDay, 1);
      }
    }
    if (timedRange.start) {
      startDay = startOfDay(timedRange.start);
      if (endDay && endDay <= startDay) {
        endDay = addDays(startDay, 1);
      }
    }
    return { start: startDay, end: endDay };
  }
  function isMultiDayRange(range) {
    let visibleRange = computeVisibleDayRange(range);
    return diffDays(visibleRange.start, visibleRange.end) > 1;
  }
  function diffDates(date0, date1, dateEnv, largeUnit) {
    if (largeUnit === "year") {
      return createDuration(dateEnv.diffWholeYears(date0, date1), "year");
    }
    if (largeUnit === "month") {
      return createDuration(dateEnv.diffWholeMonths(date0, date1), "month");
    }
    return diffDayAndTime(date0, date1);
  }
  var DateProfileGenerator = class {
    constructor(props) {
      this.props = props;
      this.initHiddenDays();
    }
    buildPrev(currentDateProfile, currentDate, forceToValid) {
      let { dateEnv } = this.props;
      let prevDate = dateEnv.subtract(
        dateEnv.startOf(currentDate, currentDateProfile.currentRangeUnit),
        currentDateProfile.dateIncrement
      );
      return this.build(prevDate, -1, forceToValid);
    }
    buildNext(currentDateProfile, currentDate, forceToValid) {
      let { dateEnv } = this.props;
      let nextDate = dateEnv.add(
        dateEnv.startOf(currentDate, currentDateProfile.currentRangeUnit),
        currentDateProfile.dateIncrement
      );
      return this.build(nextDate, 1, forceToValid);
    }
    build(currentDate, direction, forceToValid = true) {
      let { props } = this;
      let validRange;
      let currentInfo;
      let isRangeAllDay;
      let renderRange;
      let activeRange;
      let isValid;
      validRange = this.buildValidRange();
      validRange = this.trimHiddenDays(validRange);
      if (forceToValid) {
        currentDate = constrainMarkerToRange(currentDate, validRange);
      }
      currentInfo = this.buildCurrentRangeInfo(currentDate, direction);
      isRangeAllDay = /^(year|month|week|day)$/.test(currentInfo.unit);
      renderRange = this.buildRenderRange(this.trimHiddenDays(currentInfo.range), currentInfo.unit, isRangeAllDay);
      renderRange = this.trimHiddenDays(renderRange);
      activeRange = renderRange;
      if (!props.showNonCurrentDates) {
        activeRange = intersectRanges(activeRange, currentInfo.range);
      }
      activeRange = this.adjustActiveRange(activeRange);
      activeRange = intersectRanges(activeRange, validRange);
      isValid = rangesIntersect(currentInfo.range, validRange);
      if (!rangeContainsMarker(renderRange, currentDate)) {
        currentDate = renderRange.start;
      }
      return {
        currentDate,
        validRange,
        currentRange: currentInfo.range,
        currentRangeUnit: currentInfo.unit,
        isRangeAllDay,
        activeRange,
        renderRange,
        slotMinTime: props.slotMinTime,
        slotMaxTime: props.slotMaxTime,
        isValid,
        dateIncrement: this.buildDateIncrement(currentInfo.duration)
      };
    }
    buildValidRange() {
      let input = this.props.validRangeInput;
      let simpleInput = typeof input === "function" ? input.call(this.props.calendarApi, this.props.dateEnv.toDate(this.props.nowManager.getDateMarker())) : input;
      return this.refineRange(simpleInput) || { start: null, end: null };
    }
    buildCurrentRangeInfo(date, direction) {
      let { props } = this;
      let duration = null;
      let unit = null;
      let range = null;
      let dayCount;
      if (props.duration) {
        duration = props.duration;
        unit = props.durationUnit;
        range = this.buildRangeFromDuration(date, direction, duration, unit);
      } else if (dayCount = this.props.dayCount) {
        unit = "day";
        range = this.buildRangeFromDayCount(date, direction, dayCount);
      } else if (range = this.buildCustomVisibleRange(date)) {
        unit = props.dateEnv.greatestWholeUnit(range.start, range.end).unit;
      } else {
        duration = this.getFallbackDuration();
        unit = greatestDurationDenominator(duration).unit;
        range = this.buildRangeFromDuration(date, direction, duration, unit);
      }
      return { duration, unit, range };
    }
    getFallbackDuration() {
      return createDuration({ day: 1 });
    }
    adjustActiveRange(range) {
      let { dateEnv, usesMinMaxTime, slotMinTime, slotMaxTime } = this.props;
      let { start, end } = range;
      if (usesMinMaxTime) {
        if (asRoughDays(slotMinTime) < 0) {
          start = startOfDay(start);
          start = dateEnv.add(start, slotMinTime);
        }
        if (asRoughDays(slotMaxTime) > 1) {
          end = startOfDay(end);
          end = addDays(end, -1);
          end = dateEnv.add(end, slotMaxTime);
        }
      }
      return { start, end };
    }
    buildRangeFromDuration(date, direction, duration, unit) {
      let { dateEnv, dateAlignment } = this.props;
      let start;
      let end;
      let res;
      if (!dateAlignment) {
        let { dateIncrement } = this.props;
        if (dateIncrement) {
          if (asRoughMs(dateIncrement) < asRoughMs(duration)) {
            dateAlignment = greatestDurationDenominator(dateIncrement).unit;
          } else {
            dateAlignment = unit;
          }
        } else {
          dateAlignment = unit;
        }
      }
      if (asRoughDays(duration) <= 1) {
        if (this.isHiddenDay(start)) {
          start = this.skipHiddenDays(start, direction);
          start = startOfDay(start);
        }
      }
      function computeRes() {
        start = dateEnv.startOf(date, dateAlignment);
        end = dateEnv.add(start, duration);
        res = { start, end };
      }
      computeRes();
      if (!this.trimHiddenDays(res)) {
        date = this.skipHiddenDays(date, direction);
        computeRes();
      }
      return res;
    }
    buildRangeFromDayCount(date, direction, dayCount) {
      let { dateEnv, dateAlignment } = this.props;
      let runningCount = 0;
      let start = date;
      let end;
      if (dateAlignment) {
        start = dateEnv.startOf(start, dateAlignment);
      }
      start = startOfDay(start);
      start = this.skipHiddenDays(start, direction);
      end = start;
      do {
        end = addDays(end, 1);
        if (!this.isHiddenDay(end)) {
          runningCount += 1;
        }
      } while (runningCount < dayCount);
      return { start, end };
    }
    buildCustomVisibleRange(date) {
      let { props } = this;
      let input = props.visibleRangeInput;
      let simpleInput = typeof input === "function" ? input.call(props.calendarApi, props.dateEnv.toDate(date)) : input;
      let range = this.refineRange(simpleInput);
      if (range && (range.start == null || range.end == null)) {
        return null;
      }
      return range;
    }
    buildRenderRange(currentRange, currentRangeUnit, isRangeAllDay) {
      return currentRange;
    }
    buildDateIncrement(fallback) {
      let { dateIncrement } = this.props;
      let customAlignment;
      if (dateIncrement) {
        return dateIncrement;
      }
      if (customAlignment = this.props.dateAlignment) {
        return createDuration(1, customAlignment);
      }
      if (fallback) {
        return fallback;
      }
      return createDuration({ days: 1 });
    }
    refineRange(rangeInput) {
      if (rangeInput) {
        let range = parseRange(rangeInput, this.props.dateEnv);
        if (range) {
          range = computeVisibleDayRange(range);
        }
        return range;
      }
      return null;
    }
    initHiddenDays() {
      let hiddenDays = this.props.hiddenDays || [];
      let isHiddenDayHash = [];
      let dayCnt = 0;
      let i3;
      if (this.props.weekends === false) {
        hiddenDays.push(0, 6);
      }
      for (i3 = 0; i3 < 7; i3 += 1) {
        if (!(isHiddenDayHash[i3] = hiddenDays.indexOf(i3) !== -1)) {
          dayCnt += 1;
        }
      }
      if (!dayCnt) {
        throw new Error("invalid hiddenDays");
      }
      this.isHiddenDayHash = isHiddenDayHash;
    }
    trimHiddenDays(range) {
      let { start, end } = range;
      if (start) {
        start = this.skipHiddenDays(start);
      }
      if (end) {
        end = this.skipHiddenDays(end, -1, true);
      }
      if (start == null || end == null || start < end) {
        return { start, end };
      }
      return null;
    }
    isHiddenDay(day) {
      if (day instanceof Date) {
        day = day.getUTCDay();
      }
      return this.isHiddenDayHash[day];
    }
    skipHiddenDays(date, inc = 1, isExclusive = false) {
      while (this.isHiddenDayHash[(date.getUTCDay() + (isExclusive ? inc : 0) + 7) % 7]) {
        date = addDays(date, inc);
      }
      return date;
    }
  };
  function createEventInstance(defId, range, forcedStartTzo, forcedEndTzo) {
    return {
      instanceId: guid(),
      defId,
      range,
      forcedStartTzo: forcedStartTzo == null ? null : forcedStartTzo,
      forcedEndTzo: forcedEndTzo == null ? null : forcedEndTzo
    };
  }
  function parseRecurring(refined, defaultAllDay, dateEnv, recurringTypes) {
    for (let i3 = 0; i3 < recurringTypes.length; i3 += 1) {
      let parsed = recurringTypes[i3].parse(refined, dateEnv);
      if (parsed) {
        let { allDay } = refined;
        if (allDay == null) {
          allDay = defaultAllDay;
          if (allDay == null) {
            allDay = parsed.allDayGuess;
            if (allDay == null) {
              allDay = false;
            }
          }
        }
        return {
          allDay,
          duration: parsed.duration,
          typeData: parsed.typeData,
          typeId: i3
        };
      }
    }
    return null;
  }
  function expandRecurring(eventStore, framingRange, context) {
    let { dateEnv, pluginHooks, options } = context;
    let { defs, instances } = eventStore;
    instances = filterHash(instances, (instance) => !defs[instance.defId].recurringDef);
    for (let defId in defs) {
      let def = defs[defId];
      if (def.recurringDef) {
        let { duration } = def.recurringDef;
        if (!duration) {
          duration = def.allDay ? options.defaultAllDayEventDuration : options.defaultTimedEventDuration;
        }
        let starts = expandRecurringRanges(def, duration, framingRange, dateEnv, pluginHooks.recurringTypes);
        for (let start of starts) {
          let instance = createEventInstance(defId, {
            start,
            end: dateEnv.add(start, duration)
          });
          instances[instance.instanceId] = instance;
        }
      }
    }
    return { defs, instances };
  }
  function expandRecurringRanges(eventDef, duration, framingRange, dateEnv, recurringTypes) {
    let typeDef = recurringTypes[eventDef.recurringDef.typeId];
    let markers = typeDef.expand(eventDef.recurringDef.typeData, {
      start: dateEnv.subtract(framingRange.start, duration),
      end: framingRange.end
    }, dateEnv);
    if (eventDef.allDay) {
      markers = markers.map(startOfDay);
    }
    return markers;
  }
  var EVENT_NON_DATE_REFINERS = {
    id: String,
    groupId: String,
    title: String,
    url: String,
    interactive: Boolean
  };
  var EVENT_DATE_REFINERS = {
    start: identity,
    end: identity,
    date: identity,
    allDay: Boolean
  };
  var EVENT_REFINERS = Object.assign(Object.assign(Object.assign({}, EVENT_NON_DATE_REFINERS), EVENT_DATE_REFINERS), { extendedProps: identity });
  function parseEvent(raw, eventSource, context, allowOpenRange, refiners = buildEventRefiners(context), defIdMap, instanceIdMap) {
    let { refined, extra } = refineEventDef(raw, context, refiners);
    let defaultAllDay = computeIsDefaultAllDay(eventSource, context);
    let recurringRes = parseRecurring(refined, defaultAllDay, context.dateEnv, context.pluginHooks.recurringTypes);
    if (recurringRes) {
      let def = parseEventDef(refined, extra, eventSource ? eventSource.sourceId : "", recurringRes.allDay, Boolean(recurringRes.duration), context, defIdMap);
      def.recurringDef = {
        typeId: recurringRes.typeId,
        typeData: recurringRes.typeData,
        duration: recurringRes.duration
      };
      return { def, instance: null };
    }
    let singleRes = parseSingle(refined, defaultAllDay, context, allowOpenRange);
    if (singleRes) {
      let def = parseEventDef(refined, extra, eventSource ? eventSource.sourceId : "", singleRes.allDay, singleRes.hasEnd, context, defIdMap);
      let instance = createEventInstance(def.defId, singleRes.range, singleRes.forcedStartTzo, singleRes.forcedEndTzo);
      if (instanceIdMap && def.publicId && instanceIdMap[def.publicId]) {
        instance.instanceId = instanceIdMap[def.publicId];
      }
      return { def, instance };
    }
    return null;
  }
  function refineEventDef(raw, context, refiners = buildEventRefiners(context)) {
    return refineProps(raw, refiners);
  }
  function buildEventRefiners(context) {
    return Object.assign(Object.assign(Object.assign({}, EVENT_UI_REFINERS), EVENT_REFINERS), context.pluginHooks.eventRefiners);
  }
  function parseEventDef(refined, extra, sourceId, allDay, hasEnd, context, defIdMap) {
    let def = {
      title: refined.title || "",
      groupId: refined.groupId || "",
      publicId: refined.id || "",
      url: refined.url || "",
      recurringDef: null,
      defId: (defIdMap && refined.id ? defIdMap[refined.id] : "") || guid(),
      sourceId,
      allDay,
      hasEnd,
      interactive: refined.interactive,
      ui: createEventUi(refined, context),
      extendedProps: Object.assign(Object.assign({}, refined.extendedProps || {}), extra)
    };
    for (let memberAdder of context.pluginHooks.eventDefMemberAdders) {
      Object.assign(def, memberAdder(refined));
    }
    Object.freeze(def.ui.classNames);
    Object.freeze(def.extendedProps);
    return def;
  }
  function parseSingle(refined, defaultAllDay, context, allowOpenRange) {
    let { allDay } = refined;
    let startMeta;
    let startMarker = null;
    let hasEnd = false;
    let endMeta;
    let endMarker = null;
    let startInput = refined.start != null ? refined.start : refined.date;
    startMeta = context.dateEnv.createMarkerMeta(startInput);
    if (startMeta) {
      startMarker = startMeta.marker;
    } else if (!allowOpenRange) {
      return null;
    }
    if (refined.end != null) {
      endMeta = context.dateEnv.createMarkerMeta(refined.end);
    }
    if (allDay == null) {
      if (defaultAllDay != null) {
        allDay = defaultAllDay;
      } else {
        allDay = (!startMeta || startMeta.isTimeUnspecified) && (!endMeta || endMeta.isTimeUnspecified);
      }
    }
    if (allDay && startMarker) {
      startMarker = startOfDay(startMarker);
    }
    if (endMeta) {
      endMarker = endMeta.marker;
      if (allDay) {
        endMarker = startOfDay(endMarker);
      }
      if (startMarker && endMarker <= startMarker) {
        endMarker = null;
      }
    }
    if (endMarker) {
      hasEnd = true;
    } else if (!allowOpenRange) {
      hasEnd = context.options.forceEventDuration || false;
      endMarker = context.dateEnv.add(startMarker, allDay ? context.options.defaultAllDayEventDuration : context.options.defaultTimedEventDuration);
    }
    return {
      allDay,
      hasEnd,
      range: { start: startMarker, end: endMarker },
      forcedStartTzo: startMeta ? startMeta.forcedTzo : null,
      forcedEndTzo: endMeta ? endMeta.forcedTzo : null
    };
  }
  function computeIsDefaultAllDay(eventSource, context) {
    let res = null;
    if (eventSource) {
      res = eventSource.defaultAllDay;
    }
    if (res == null) {
      res = context.options.defaultAllDay;
    }
    return res;
  }
  function parseEvents(rawEvents, eventSource, context, allowOpenRange, defIdMap, instanceIdMap) {
    let eventStore = createEmptyEventStore();
    let eventRefiners = buildEventRefiners(context);
    for (let rawEvent of rawEvents) {
      let tuple = parseEvent(rawEvent, eventSource, context, allowOpenRange, eventRefiners, defIdMap, instanceIdMap);
      if (tuple) {
        eventTupleToStore(tuple, eventStore);
      }
    }
    return eventStore;
  }
  function eventTupleToStore(tuple, eventStore = createEmptyEventStore()) {
    eventStore.defs[tuple.def.defId] = tuple.def;
    if (tuple.instance) {
      eventStore.instances[tuple.instance.instanceId] = tuple.instance;
    }
    return eventStore;
  }
  function getRelevantEvents(eventStore, instanceId) {
    let instance = eventStore.instances[instanceId];
    if (instance) {
      let def = eventStore.defs[instance.defId];
      let newStore = filterEventStoreDefs(eventStore, (lookDef) => isEventDefsGrouped(def, lookDef));
      newStore.defs[def.defId] = def;
      newStore.instances[instance.instanceId] = instance;
      return newStore;
    }
    return createEmptyEventStore();
  }
  function isEventDefsGrouped(def0, def1) {
    return Boolean(def0.groupId && def0.groupId === def1.groupId);
  }
  function createEmptyEventStore() {
    return { defs: {}, instances: {} };
  }
  function mergeEventStores(store0, store1) {
    return {
      defs: Object.assign(Object.assign({}, store0.defs), store1.defs),
      instances: Object.assign(Object.assign({}, store0.instances), store1.instances)
    };
  }
  function filterEventStoreDefs(eventStore, filterFunc) {
    let defs = filterHash(eventStore.defs, filterFunc);
    let instances = filterHash(eventStore.instances, (instance) => defs[instance.defId]);
    return { defs, instances };
  }
  function excludeSubEventStore(master, sub) {
    let { defs, instances } = master;
    let filteredDefs = {};
    let filteredInstances = {};
    for (let defId in defs) {
      if (!sub.defs[defId]) {
        filteredDefs[defId] = defs[defId];
      }
    }
    for (let instanceId in instances) {
      if (!sub.instances[instanceId] && filteredDefs[instances[instanceId].defId]) {
        filteredInstances[instanceId] = instances[instanceId];
      }
    }
    return {
      defs: filteredDefs,
      instances: filteredInstances
    };
  }
  function normalizeConstraint(input, context) {
    if (Array.isArray(input)) {
      return parseEvents(input, null, context, true);
    }
    if (typeof input === "object" && input) {
      return parseEvents([input], null, context, true);
    }
    if (input != null) {
      return String(input);
    }
    return null;
  }
  function parseClassNames(raw) {
    if (Array.isArray(raw)) {
      return raw;
    }
    if (typeof raw === "string") {
      return raw.split(/\s+/);
    }
    return [];
  }
  var EVENT_UI_REFINERS = {
    display: String,
    editable: Boolean,
    startEditable: Boolean,
    durationEditable: Boolean,
    constraint: identity,
    overlap: identity,
    allow: identity,
    className: parseClassNames,
    classNames: parseClassNames,
    color: String,
    backgroundColor: String,
    borderColor: String,
    textColor: String
  };
  var EMPTY_EVENT_UI = {
    display: null,
    startEditable: null,
    durationEditable: null,
    constraints: [],
    overlap: null,
    allows: [],
    backgroundColor: "",
    borderColor: "",
    textColor: "",
    classNames: []
  };
  function createEventUi(refined, context) {
    let constraint = normalizeConstraint(refined.constraint, context);
    return {
      display: refined.display || null,
      startEditable: refined.startEditable != null ? refined.startEditable : refined.editable,
      durationEditable: refined.durationEditable != null ? refined.durationEditable : refined.editable,
      constraints: constraint != null ? [constraint] : [],
      overlap: refined.overlap != null ? refined.overlap : null,
      allows: refined.allow != null ? [refined.allow] : [],
      backgroundColor: refined.backgroundColor || refined.color || "",
      borderColor: refined.borderColor || refined.color || "",
      textColor: refined.textColor || "",
      classNames: (refined.className || []).concat(refined.classNames || [])
    };
  }
  function combineEventUis(uis) {
    return uis.reduce(combineTwoEventUis, EMPTY_EVENT_UI);
  }
  function combineTwoEventUis(item0, item1) {
    return {
      display: item1.display != null ? item1.display : item0.display,
      startEditable: item1.startEditable != null ? item1.startEditable : item0.startEditable,
      durationEditable: item1.durationEditable != null ? item1.durationEditable : item0.durationEditable,
      constraints: item0.constraints.concat(item1.constraints),
      overlap: typeof item1.overlap === "boolean" ? item1.overlap : item0.overlap,
      allows: item0.allows.concat(item1.allows),
      backgroundColor: item1.backgroundColor || item0.backgroundColor,
      borderColor: item1.borderColor || item0.borderColor,
      textColor: item1.textColor || item0.textColor,
      classNames: item0.classNames.concat(item1.classNames)
    };
  }
  var EVENT_SOURCE_REFINERS = {
    id: String,
    defaultAllDay: Boolean,
    url: String,
    format: String,
    events: identity,
    eventDataTransform: identity,
    success: identity,
    failure: identity
  };
  function parseEventSource(raw, context, refiners = buildEventSourceRefiners(context)) {
    let rawObj;
    if (typeof raw === "string") {
      rawObj = { url: raw };
    } else if (typeof raw === "function" || Array.isArray(raw)) {
      rawObj = { events: raw };
    } else if (typeof raw === "object" && raw) {
      rawObj = raw;
    }
    if (rawObj) {
      let { refined, extra } = refineProps(rawObj, refiners);
      let metaRes = buildEventSourceMeta(refined, context);
      if (metaRes) {
        return {
          _raw: raw,
          isFetching: false,
          latestFetchId: "",
          fetchRange: null,
          defaultAllDay: refined.defaultAllDay,
          eventDataTransform: refined.eventDataTransform,
          success: refined.success,
          failure: refined.failure,
          publicId: refined.id || "",
          sourceId: guid(),
          sourceDefId: metaRes.sourceDefId,
          meta: metaRes.meta,
          ui: createEventUi(refined, context),
          extendedProps: extra
        };
      }
    }
    return null;
  }
  function buildEventSourceRefiners(context) {
    return Object.assign(Object.assign(Object.assign({}, EVENT_UI_REFINERS), EVENT_SOURCE_REFINERS), context.pluginHooks.eventSourceRefiners);
  }
  function buildEventSourceMeta(raw, context) {
    let defs = context.pluginHooks.eventSourceDefs;
    for (let i3 = defs.length - 1; i3 >= 0; i3 -= 1) {
      let def = defs[i3];
      let meta = def.parseMeta(raw);
      if (meta) {
        return { sourceDefId: i3, meta };
      }
    }
    return null;
  }
  function reduceEventStore(eventStore, action, eventSources, dateProfile, context) {
    switch (action.type) {
      case "RECEIVE_EVENTS":
        return receiveRawEvents(eventStore, eventSources[action.sourceId], action.fetchId, action.fetchRange, action.rawEvents, context);
      case "RESET_RAW_EVENTS":
        return resetRawEvents(eventStore, eventSources[action.sourceId], action.rawEvents, dateProfile.activeRange, context);
      case "ADD_EVENTS":
        return addEvent(
          eventStore,
          action.eventStore,
          dateProfile ? dateProfile.activeRange : null,
          context
        );
      case "RESET_EVENTS":
        return action.eventStore;
      case "MERGE_EVENTS":
        return mergeEventStores(eventStore, action.eventStore);
      case "PREV":
      case "NEXT":
      case "CHANGE_DATE":
      case "CHANGE_VIEW_TYPE":
        if (dateProfile) {
          return expandRecurring(eventStore, dateProfile.activeRange, context);
        }
        return eventStore;
      case "REMOVE_EVENTS":
        return excludeSubEventStore(eventStore, action.eventStore);
      case "REMOVE_EVENT_SOURCE":
        return excludeEventsBySourceId(eventStore, action.sourceId);
      case "REMOVE_ALL_EVENT_SOURCES":
        return filterEventStoreDefs(eventStore, (eventDef) => !eventDef.sourceId);
      case "REMOVE_ALL_EVENTS":
        return createEmptyEventStore();
      default:
        return eventStore;
    }
  }
  function receiveRawEvents(eventStore, eventSource, fetchId, fetchRange, rawEvents, context) {
    if (eventSource && fetchId === eventSource.latestFetchId) {
      let subset = parseEvents(transformRawEvents(rawEvents, eventSource, context), eventSource, context);
      if (fetchRange) {
        subset = expandRecurring(subset, fetchRange, context);
      }
      return mergeEventStores(excludeEventsBySourceId(eventStore, eventSource.sourceId), subset);
    }
    return eventStore;
  }
  function resetRawEvents(existingEventStore, eventSource, rawEvents, activeRange, context) {
    const { defIdMap, instanceIdMap } = buildPublicIdMaps(existingEventStore);
    let newEventStore = parseEvents(transformRawEvents(rawEvents, eventSource, context), eventSource, context, false, defIdMap, instanceIdMap);
    return expandRecurring(newEventStore, activeRange, context);
  }
  function transformRawEvents(rawEvents, eventSource, context) {
    let calEachTransform = context.options.eventDataTransform;
    let sourceEachTransform = eventSource ? eventSource.eventDataTransform : null;
    if (sourceEachTransform) {
      rawEvents = transformEachRawEvent(rawEvents, sourceEachTransform);
    }
    if (calEachTransform) {
      rawEvents = transformEachRawEvent(rawEvents, calEachTransform);
    }
    return rawEvents;
  }
  function transformEachRawEvent(rawEvents, func) {
    let refinedEvents;
    if (!func) {
      refinedEvents = rawEvents;
    } else {
      refinedEvents = [];
      for (let rawEvent of rawEvents) {
        let refinedEvent = func(rawEvent);
        if (refinedEvent) {
          refinedEvents.push(refinedEvent);
        } else if (refinedEvent == null) {
          refinedEvents.push(rawEvent);
        }
      }
    }
    return refinedEvents;
  }
  function addEvent(eventStore, subset, expandRange, context) {
    if (expandRange) {
      subset = expandRecurring(subset, expandRange, context);
    }
    return mergeEventStores(eventStore, subset);
  }
  function rezoneEventStoreDates(eventStore, oldDateEnv, newDateEnv) {
    let { defs } = eventStore;
    let instances = mapHash(eventStore.instances, (instance) => {
      let def = defs[instance.defId];
      if (def.allDay) {
        return instance;
      }
      return Object.assign(Object.assign({}, instance), { range: {
        start: newDateEnv.createMarker(oldDateEnv.toDate(instance.range.start, instance.forcedStartTzo)),
        end: newDateEnv.createMarker(oldDateEnv.toDate(instance.range.end, instance.forcedEndTzo))
      }, forcedStartTzo: newDateEnv.canComputeOffset ? null : instance.forcedStartTzo, forcedEndTzo: newDateEnv.canComputeOffset ? null : instance.forcedEndTzo });
    });
    return { defs, instances };
  }
  function excludeEventsBySourceId(eventStore, sourceId) {
    return filterEventStoreDefs(eventStore, (eventDef) => eventDef.sourceId !== sourceId);
  }
  function buildPublicIdMaps(eventStore) {
    const { defs, instances } = eventStore;
    const defIdMap = {};
    const instanceIdMap = {};
    for (let defId in defs) {
      const def = defs[defId];
      const { publicId } = def;
      if (publicId) {
        defIdMap[publicId] = defId;
      }
    }
    for (let instanceId in instances) {
      const instance = instances[instanceId];
      const def = defs[instance.defId];
      const { publicId } = def;
      if (publicId) {
        instanceIdMap[publicId] = instanceId;
      }
    }
    return { defIdMap, instanceIdMap };
  }
  var Emitter = class {
    constructor() {
      this.handlers = {};
      this.thisContext = null;
    }
    setThisContext(thisContext) {
      this.thisContext = thisContext;
    }
    setOptions(options) {
      this.options = options;
    }
    on(type, handler) {
      addToHash(this.handlers, type, handler);
    }
    off(type, handler) {
      removeFromHash(this.handlers, type, handler);
    }
    trigger(type, ...args) {
      let attachedHandlers = this.handlers[type] || [];
      let optionHandler = this.options && this.options[type];
      let handlers = [].concat(optionHandler || [], attachedHandlers);
      for (let handler of handlers) {
        handler.apply(this.thisContext, args);
      }
    }
    hasHandlers(type) {
      return Boolean(this.handlers[type] && this.handlers[type].length || this.options && this.options[type]);
    }
  };
  function addToHash(hash, type, handler) {
    (hash[type] || (hash[type] = [])).push(handler);
  }
  function removeFromHash(hash, type, handler) {
    if (handler) {
      if (hash[type]) {
        hash[type] = hash[type].filter((func) => func !== handler);
      }
    } else {
      delete hash[type];
    }
  }
  var DEF_DEFAULTS = {
    startTime: "09:00",
    endTime: "17:00",
    daysOfWeek: [1, 2, 3, 4, 5],
    display: "inverse-background",
    classNames: "fc-non-business",
    groupId: "_businessHours"
  };
  function parseBusinessHours(input, context) {
    return parseEvents(refineInputs(input), null, context);
  }
  function refineInputs(input) {
    let rawDefs;
    if (input === true) {
      rawDefs = [{}];
    } else if (Array.isArray(input)) {
      rawDefs = input.filter((rawDef) => rawDef.daysOfWeek);
    } else if (typeof input === "object" && input) {
      rawDefs = [input];
    } else {
      rawDefs = [];
    }
    rawDefs = rawDefs.map((rawDef) => Object.assign(Object.assign({}, DEF_DEFAULTS), rawDef));
    return rawDefs;
  }
  function triggerDateSelect(selection, pev, context) {
    context.emitter.trigger("select", Object.assign(Object.assign({}, buildDateSpanApiWithContext(selection, context)), { jsEvent: pev ? pev.origEvent : null, view: context.viewApi || context.calendarApi.view }));
  }
  function triggerDateUnselect(pev, context) {
    context.emitter.trigger("unselect", {
      jsEvent: pev ? pev.origEvent : null,
      view: context.viewApi || context.calendarApi.view
    });
  }
  function buildDateSpanApiWithContext(dateSpan, context) {
    let props = {};
    for (let transform of context.pluginHooks.dateSpanTransforms) {
      Object.assign(props, transform(dateSpan, context));
    }
    Object.assign(props, buildDateSpanApi(dateSpan, context.dateEnv));
    return props;
  }
  function getDefaultEventEnd(allDay, marker, context) {
    let { dateEnv, options } = context;
    let end = marker;
    if (allDay) {
      end = startOfDay(end);
      end = dateEnv.add(end, options.defaultAllDayEventDuration);
    } else {
      end = dateEnv.add(end, options.defaultTimedEventDuration);
    }
    return end;
  }
  function applyMutationToEventStore(eventStore, eventConfigBase, mutation, context) {
    let eventConfigs = compileEventUis(eventStore.defs, eventConfigBase);
    let dest = createEmptyEventStore();
    for (let defId in eventStore.defs) {
      let def = eventStore.defs[defId];
      dest.defs[defId] = applyMutationToEventDef(def, eventConfigs[defId], mutation, context);
    }
    for (let instanceId in eventStore.instances) {
      let instance = eventStore.instances[instanceId];
      let def = dest.defs[instance.defId];
      dest.instances[instanceId] = applyMutationToEventInstance(instance, def, eventConfigs[instance.defId], mutation, context);
    }
    return dest;
  }
  function applyMutationToEventDef(eventDef, eventConfig, mutation, context) {
    let standardProps = mutation.standardProps || {};
    if (standardProps.hasEnd == null && eventConfig.durationEditable && (mutation.startDelta || mutation.endDelta)) {
      standardProps.hasEnd = true;
    }
    let copy = Object.assign(Object.assign(Object.assign({}, eventDef), standardProps), { ui: Object.assign(Object.assign({}, eventDef.ui), standardProps.ui) });
    if (mutation.extendedProps) {
      copy.extendedProps = Object.assign(Object.assign({}, copy.extendedProps), mutation.extendedProps);
    }
    for (let applier of context.pluginHooks.eventDefMutationAppliers) {
      applier(copy, mutation, context);
    }
    if (!copy.hasEnd && context.options.forceEventDuration) {
      copy.hasEnd = true;
    }
    return copy;
  }
  function applyMutationToEventInstance(eventInstance, eventDef, eventConfig, mutation, context) {
    let { dateEnv } = context;
    let forceAllDay = mutation.standardProps && mutation.standardProps.allDay === true;
    let clearEnd = mutation.standardProps && mutation.standardProps.hasEnd === false;
    let copy = Object.assign({}, eventInstance);
    if (forceAllDay) {
      copy.range = computeAlignedDayRange(copy.range);
    }
    if (mutation.datesDelta && eventConfig.startEditable) {
      copy.range = {
        start: dateEnv.add(copy.range.start, mutation.datesDelta),
        end: dateEnv.add(copy.range.end, mutation.datesDelta)
      };
    }
    if (mutation.startDelta && eventConfig.durationEditable) {
      copy.range = {
        start: dateEnv.add(copy.range.start, mutation.startDelta),
        end: copy.range.end
      };
    }
    if (mutation.endDelta && eventConfig.durationEditable) {
      copy.range = {
        start: copy.range.start,
        end: dateEnv.add(copy.range.end, mutation.endDelta)
      };
    }
    if (clearEnd) {
      copy.range = {
        start: copy.range.start,
        end: getDefaultEventEnd(eventDef.allDay, copy.range.start, context)
      };
    }
    if (eventDef.allDay) {
      copy.range = {
        start: startOfDay(copy.range.start),
        end: startOfDay(copy.range.end)
      };
    }
    if (copy.range.end < copy.range.start) {
      copy.range.end = getDefaultEventEnd(eventDef.allDay, copy.range.start, context);
    }
    return copy;
  }
  var EventSourceImpl = class {
    constructor(context, internalEventSource) {
      this.context = context;
      this.internalEventSource = internalEventSource;
    }
    remove() {
      this.context.dispatch({
        type: "REMOVE_EVENT_SOURCE",
        sourceId: this.internalEventSource.sourceId
      });
    }
    refetch() {
      this.context.dispatch({
        type: "FETCH_EVENT_SOURCES",
        sourceIds: [this.internalEventSource.sourceId],
        isRefetch: true
      });
    }
    get id() {
      return this.internalEventSource.publicId;
    }
    get url() {
      return this.internalEventSource.meta.url;
    }
    get format() {
      return this.internalEventSource.meta.format;
    }
  };
  var EventImpl = class {
    constructor(context, def, instance) {
      this._context = context;
      this._def = def;
      this._instance = instance || null;
    }
    setProp(name, val) {
      if (name in EVENT_DATE_REFINERS) {
        console.warn("Could not set date-related prop 'name'. Use one of the date-related methods instead.");
      } else if (name === "id") {
        val = EVENT_NON_DATE_REFINERS[name](val);
        this.mutate({
          standardProps: { publicId: val }
        });
      } else if (name in EVENT_NON_DATE_REFINERS) {
        val = EVENT_NON_DATE_REFINERS[name](val);
        this.mutate({
          standardProps: { [name]: val }
        });
      } else if (name in EVENT_UI_REFINERS) {
        let ui = EVENT_UI_REFINERS[name](val);
        if (name === "color") {
          ui = { backgroundColor: val, borderColor: val };
        } else if (name === "editable") {
          ui = { startEditable: val, durationEditable: val };
        } else {
          ui = { [name]: val };
        }
        this.mutate({
          standardProps: { ui }
        });
      } else {
        console.warn(`Could not set prop '${name}'. Use setExtendedProp instead.`);
      }
    }
    setExtendedProp(name, val) {
      this.mutate({
        extendedProps: { [name]: val }
      });
    }
    setStart(startInput, options = {}) {
      let { dateEnv } = this._context;
      let start = dateEnv.createMarker(startInput);
      if (start && this._instance) {
        let instanceRange = this._instance.range;
        let startDelta = diffDates(instanceRange.start, start, dateEnv, options.granularity);
        if (options.maintainDuration) {
          this.mutate({ datesDelta: startDelta });
        } else {
          this.mutate({ startDelta });
        }
      }
    }
    setEnd(endInput, options = {}) {
      let { dateEnv } = this._context;
      let end;
      if (endInput != null) {
        end = dateEnv.createMarker(endInput);
        if (!end) {
          return;
        }
      }
      if (this._instance) {
        if (end) {
          let endDelta = diffDates(this._instance.range.end, end, dateEnv, options.granularity);
          this.mutate({ endDelta });
        } else {
          this.mutate({ standardProps: { hasEnd: false } });
        }
      }
    }
    setDates(startInput, endInput, options = {}) {
      let { dateEnv } = this._context;
      let standardProps = { allDay: options.allDay };
      let start = dateEnv.createMarker(startInput);
      let end;
      if (!start) {
        return;
      }
      if (endInput != null) {
        end = dateEnv.createMarker(endInput);
        if (!end) {
          return;
        }
      }
      if (this._instance) {
        let instanceRange = this._instance.range;
        if (options.allDay === true) {
          instanceRange = computeAlignedDayRange(instanceRange);
        }
        let startDelta = diffDates(instanceRange.start, start, dateEnv, options.granularity);
        if (end) {
          let endDelta = diffDates(instanceRange.end, end, dateEnv, options.granularity);
          if (durationsEqual(startDelta, endDelta)) {
            this.mutate({ datesDelta: startDelta, standardProps });
          } else {
            this.mutate({ startDelta, endDelta, standardProps });
          }
        } else {
          standardProps.hasEnd = false;
          this.mutate({ datesDelta: startDelta, standardProps });
        }
      }
    }
    moveStart(deltaInput) {
      let delta = createDuration(deltaInput);
      if (delta) {
        this.mutate({ startDelta: delta });
      }
    }
    moveEnd(deltaInput) {
      let delta = createDuration(deltaInput);
      if (delta) {
        this.mutate({ endDelta: delta });
      }
    }
    moveDates(deltaInput) {
      let delta = createDuration(deltaInput);
      if (delta) {
        this.mutate({ datesDelta: delta });
      }
    }
    setAllDay(allDay, options = {}) {
      let standardProps = { allDay };
      let { maintainDuration } = options;
      if (maintainDuration == null) {
        maintainDuration = this._context.options.allDayMaintainDuration;
      }
      if (this._def.allDay !== allDay) {
        standardProps.hasEnd = maintainDuration;
      }
      this.mutate({ standardProps });
    }
    formatRange(formatInput) {
      let { dateEnv } = this._context;
      let instance = this._instance;
      let formatter = createFormatter(formatInput);
      if (this._def.hasEnd) {
        return dateEnv.formatRange(instance.range.start, instance.range.end, formatter, {
          forcedStartTzo: instance.forcedStartTzo,
          forcedEndTzo: instance.forcedEndTzo
        });
      }
      return dateEnv.format(instance.range.start, formatter, {
        forcedTzo: instance.forcedStartTzo
      });
    }
    mutate(mutation) {
      let instance = this._instance;
      if (instance) {
        let def = this._def;
        let context = this._context;
        let { eventStore } = context.getCurrentData();
        let relevantEvents = getRelevantEvents(eventStore, instance.instanceId);
        let eventConfigBase = {
          "": {
            display: "",
            startEditable: true,
            durationEditable: true,
            constraints: [],
            overlap: null,
            allows: [],
            backgroundColor: "",
            borderColor: "",
            textColor: "",
            classNames: []
          }
        };
        relevantEvents = applyMutationToEventStore(relevantEvents, eventConfigBase, mutation, context);
        let oldEvent = new EventImpl(context, def, instance);
        this._def = relevantEvents.defs[def.defId];
        this._instance = relevantEvents.instances[instance.instanceId];
        context.dispatch({
          type: "MERGE_EVENTS",
          eventStore: relevantEvents
        });
        context.emitter.trigger("eventChange", {
          oldEvent,
          event: this,
          relatedEvents: buildEventApis(relevantEvents, context, instance),
          revert() {
            context.dispatch({
              type: "RESET_EVENTS",
              eventStore
            });
          }
        });
      }
    }
    remove() {
      let context = this._context;
      let asStore = eventApiToStore(this);
      context.dispatch({
        type: "REMOVE_EVENTS",
        eventStore: asStore
      });
      context.emitter.trigger("eventRemove", {
        event: this,
        relatedEvents: [],
        revert() {
          context.dispatch({
            type: "MERGE_EVENTS",
            eventStore: asStore
          });
        }
      });
    }
    get source() {
      let { sourceId } = this._def;
      if (sourceId) {
        return new EventSourceImpl(this._context, this._context.getCurrentData().eventSources[sourceId]);
      }
      return null;
    }
    get start() {
      return this._instance ? this._context.dateEnv.toDate(this._instance.range.start) : null;
    }
    get end() {
      return this._instance && this._def.hasEnd ? this._context.dateEnv.toDate(this._instance.range.end) : null;
    }
    get startStr() {
      let instance = this._instance;
      if (instance) {
        return this._context.dateEnv.formatIso(instance.range.start, {
          omitTime: this._def.allDay,
          forcedTzo: instance.forcedStartTzo
        });
      }
      return "";
    }
    get endStr() {
      let instance = this._instance;
      if (instance && this._def.hasEnd) {
        return this._context.dateEnv.formatIso(instance.range.end, {
          omitTime: this._def.allDay,
          forcedTzo: instance.forcedEndTzo
        });
      }
      return "";
    }
    get id() {
      return this._def.publicId;
    }
    get groupId() {
      return this._def.groupId;
    }
    get allDay() {
      return this._def.allDay;
    }
    get title() {
      return this._def.title;
    }
    get url() {
      return this._def.url;
    }
    get display() {
      return this._def.ui.display || "auto";
    }
    get startEditable() {
      return this._def.ui.startEditable;
    }
    get durationEditable() {
      return this._def.ui.durationEditable;
    }
    get constraint() {
      return this._def.ui.constraints[0] || null;
    }
    get overlap() {
      return this._def.ui.overlap;
    }
    get allow() {
      return this._def.ui.allows[0] || null;
    }
    get backgroundColor() {
      return this._def.ui.backgroundColor;
    }
    get borderColor() {
      return this._def.ui.borderColor;
    }
    get textColor() {
      return this._def.ui.textColor;
    }
    get classNames() {
      return this._def.ui.classNames;
    }
    get extendedProps() {
      return this._def.extendedProps;
    }
    toPlainObject(settings = {}) {
      let def = this._def;
      let { ui } = def;
      let { startStr, endStr } = this;
      let res = {
        allDay: def.allDay
      };
      if (def.title) {
        res.title = def.title;
      }
      if (startStr) {
        res.start = startStr;
      }
      if (endStr) {
        res.end = endStr;
      }
      if (def.publicId) {
        res.id = def.publicId;
      }
      if (def.groupId) {
        res.groupId = def.groupId;
      }
      if (def.url) {
        res.url = def.url;
      }
      if (ui.display && ui.display !== "auto") {
        res.display = ui.display;
      }
      if (settings.collapseColor && ui.backgroundColor && ui.backgroundColor === ui.borderColor) {
        res.color = ui.backgroundColor;
      } else {
        if (ui.backgroundColor) {
          res.backgroundColor = ui.backgroundColor;
        }
        if (ui.borderColor) {
          res.borderColor = ui.borderColor;
        }
      }
      if (ui.textColor) {
        res.textColor = ui.textColor;
      }
      if (ui.classNames.length) {
        res.classNames = ui.classNames;
      }
      if (Object.keys(def.extendedProps).length) {
        if (settings.collapseExtendedProps) {
          Object.assign(res, def.extendedProps);
        } else {
          res.extendedProps = def.extendedProps;
        }
      }
      return res;
    }
    toJSON() {
      return this.toPlainObject();
    }
  };
  function eventApiToStore(eventApi) {
    let def = eventApi._def;
    let instance = eventApi._instance;
    return {
      defs: { [def.defId]: def },
      instances: instance ? { [instance.instanceId]: instance } : {}
    };
  }
  function buildEventApis(eventStore, context, excludeInstance) {
    let { defs, instances } = eventStore;
    let eventApis = [];
    let excludeInstanceId = excludeInstance ? excludeInstance.instanceId : "";
    for (let id in instances) {
      let instance = instances[id];
      let def = defs[instance.defId];
      if (instance.instanceId !== excludeInstanceId) {
        eventApis.push(new EventImpl(context, def, instance));
      }
    }
    return eventApis;
  }
  function sliceEventStore(eventStore, eventUiBases, framingRange, nextDayThreshold) {
    let inverseBgByGroupId = {};
    let inverseBgByDefId = {};
    let defByGroupId = {};
    let bgRanges = [];
    let fgRanges = [];
    let eventUis = compileEventUis(eventStore.defs, eventUiBases);
    for (let defId in eventStore.defs) {
      let def = eventStore.defs[defId];
      let ui = eventUis[def.defId];
      if (ui.display === "inverse-background") {
        if (def.groupId) {
          inverseBgByGroupId[def.groupId] = [];
          if (!defByGroupId[def.groupId]) {
            defByGroupId[def.groupId] = def;
          }
        } else {
          inverseBgByDefId[defId] = [];
        }
      }
    }
    for (let instanceId in eventStore.instances) {
      let instance = eventStore.instances[instanceId];
      let def = eventStore.defs[instance.defId];
      let ui = eventUis[def.defId];
      let origRange = instance.range;
      let normalRange = !def.allDay && nextDayThreshold ? computeVisibleDayRange(origRange, nextDayThreshold) : origRange;
      let slicedRange = intersectRanges(normalRange, framingRange);
      if (slicedRange) {
        if (ui.display === "inverse-background") {
          if (def.groupId) {
            inverseBgByGroupId[def.groupId].push(slicedRange);
          } else {
            inverseBgByDefId[instance.defId].push(slicedRange);
          }
        } else if (ui.display !== "none") {
          (ui.display === "background" ? bgRanges : fgRanges).push({
            def,
            ui,
            instance,
            range: slicedRange,
            isStart: normalRange.start && normalRange.start.valueOf() === slicedRange.start.valueOf(),
            isEnd: normalRange.end && normalRange.end.valueOf() === slicedRange.end.valueOf()
          });
        }
      }
    }
    for (let groupId in inverseBgByGroupId) {
      let ranges = inverseBgByGroupId[groupId];
      let invertedRanges = invertRanges(ranges, framingRange);
      for (let invertedRange of invertedRanges) {
        let def = defByGroupId[groupId];
        let ui = eventUis[def.defId];
        bgRanges.push({
          def,
          ui,
          instance: null,
          range: invertedRange,
          isStart: false,
          isEnd: false
        });
      }
    }
    for (let defId in inverseBgByDefId) {
      let ranges = inverseBgByDefId[defId];
      let invertedRanges = invertRanges(ranges, framingRange);
      for (let invertedRange of invertedRanges) {
        bgRanges.push({
          def: eventStore.defs[defId],
          ui: eventUis[defId],
          instance: null,
          range: invertedRange,
          isStart: false,
          isEnd: false
        });
      }
    }
    return { bg: bgRanges, fg: fgRanges };
  }
  function hasBgRendering(def) {
    return def.ui.display === "background" || def.ui.display === "inverse-background";
  }
  function setElSeg(el, seg) {
    el.fcSeg = seg;
  }
  function getElSeg(el) {
    return el.fcSeg || el.parentNode.fcSeg || null;
  }
  function compileEventUis(eventDefs, eventUiBases) {
    return mapHash(eventDefs, (eventDef) => compileEventUi(eventDef, eventUiBases));
  }
  function compileEventUi(eventDef, eventUiBases) {
    let uis = [];
    if (eventUiBases[""]) {
      uis.push(eventUiBases[""]);
    }
    if (eventUiBases[eventDef.defId]) {
      uis.push(eventUiBases[eventDef.defId]);
    }
    uis.push(eventDef.ui);
    return combineEventUis(uis);
  }
  function sortEventSegs(segs, eventOrderSpecs) {
    let objs = segs.map(buildSegCompareObj);
    objs.sort((obj0, obj1) => compareByFieldSpecs(obj0, obj1, eventOrderSpecs));
    return objs.map((c3) => c3._seg);
  }
  function buildSegCompareObj(seg) {
    let { eventRange } = seg;
    let eventDef = eventRange.def;
    let range = eventRange.instance ? eventRange.instance.range : eventRange.range;
    let start = range.start ? range.start.valueOf() : 0;
    let end = range.end ? range.end.valueOf() : 0;
    return Object.assign(Object.assign(Object.assign({}, eventDef.extendedProps), eventDef), {
      id: eventDef.publicId,
      start,
      end,
      duration: end - start,
      allDay: Number(eventDef.allDay),
      _seg: seg
    });
  }
  function computeSegDraggable(seg, context) {
    let { pluginHooks } = context;
    let transformers = pluginHooks.isDraggableTransformers;
    let { def, ui } = seg.eventRange;
    let val = ui.startEditable;
    for (let transformer of transformers) {
      val = transformer(val, def, ui, context);
    }
    return val;
  }
  function computeSegStartResizable(seg, context) {
    return seg.isStart && seg.eventRange.ui.durationEditable && context.options.eventResizableFromStart;
  }
  function computeSegEndResizable(seg, context) {
    return seg.isEnd && seg.eventRange.ui.durationEditable;
  }
  function buildSegTimeText(seg, timeFormat, context, defaultDisplayEventTime, defaultDisplayEventEnd, startOverride, endOverride) {
    let { dateEnv, options } = context;
    let { displayEventTime, displayEventEnd } = options;
    let eventDef = seg.eventRange.def;
    let eventInstance = seg.eventRange.instance;
    if (displayEventTime == null) {
      displayEventTime = defaultDisplayEventTime !== false;
    }
    if (displayEventEnd == null) {
      displayEventEnd = defaultDisplayEventEnd !== false;
    }
    let wholeEventStart = eventInstance.range.start;
    let wholeEventEnd = eventInstance.range.end;
    let segStart = startOverride || seg.start || seg.eventRange.range.start;
    let segEnd = endOverride || seg.end || seg.eventRange.range.end;
    let isStartDay = startOfDay(wholeEventStart).valueOf() === startOfDay(segStart).valueOf();
    let isEndDay = startOfDay(addMs(wholeEventEnd, -1)).valueOf() === startOfDay(addMs(segEnd, -1)).valueOf();
    if (displayEventTime && !eventDef.allDay && (isStartDay || isEndDay)) {
      segStart = isStartDay ? wholeEventStart : segStart;
      segEnd = isEndDay ? wholeEventEnd : segEnd;
      if (displayEventEnd && eventDef.hasEnd) {
        return dateEnv.formatRange(segStart, segEnd, timeFormat, {
          forcedStartTzo: startOverride ? null : eventInstance.forcedStartTzo,
          forcedEndTzo: endOverride ? null : eventInstance.forcedEndTzo
        });
      }
      return dateEnv.format(segStart, timeFormat, {
        forcedTzo: startOverride ? null : eventInstance.forcedStartTzo
      });
    }
    return "";
  }
  function getSegMeta(seg, todayRange, nowDate) {
    let segRange = seg.eventRange.range;
    return {
      isPast: segRange.end <= (nowDate || todayRange.start),
      isFuture: segRange.start >= (nowDate || todayRange.end),
      isToday: todayRange && rangeContainsMarker(todayRange, segRange.start)
    };
  }
  function getEventClassNames(props) {
    let classNames = ["fc-event"];
    if (props.isMirror) {
      classNames.push("fc-event-mirror");
    }
    if (props.isDraggable) {
      classNames.push("fc-event-draggable");
    }
    if (props.isStartResizable || props.isEndResizable) {
      classNames.push("fc-event-resizable");
    }
    if (props.isDragging) {
      classNames.push("fc-event-dragging");
    }
    if (props.isResizing) {
      classNames.push("fc-event-resizing");
    }
    if (props.isSelected) {
      classNames.push("fc-event-selected");
    }
    if (props.isStart) {
      classNames.push("fc-event-start");
    }
    if (props.isEnd) {
      classNames.push("fc-event-end");
    }
    if (props.isPast) {
      classNames.push("fc-event-past");
    }
    if (props.isToday) {
      classNames.push("fc-event-today");
    }
    if (props.isFuture) {
      classNames.push("fc-event-future");
    }
    return classNames;
  }
  function buildEventRangeKey(eventRange) {
    return eventRange.instance ? eventRange.instance.instanceId : `${eventRange.def.defId}:${eventRange.range.start.toISOString()}`;
  }
  function getSegAnchorAttrs(seg, context) {
    let { def, instance } = seg.eventRange;
    let { url } = def;
    if (url) {
      return { href: url };
    }
    let { emitter, options } = context;
    let { eventInteractive } = options;
    if (eventInteractive == null) {
      eventInteractive = def.interactive;
      if (eventInteractive == null) {
        eventInteractive = Boolean(emitter.hasHandlers("eventClick"));
      }
    }
    if (eventInteractive) {
      return createAriaKeyboardAttrs((ev) => {
        emitter.trigger("eventClick", {
          el: ev.target,
          event: new EventImpl(context, def, instance),
          jsEvent: ev,
          view: context.viewApi
        });
      });
    }
    return {};
  }
  var STANDARD_PROPS = {
    start: identity,
    end: identity,
    allDay: Boolean
  };
  function parseDateSpan(raw, dateEnv, defaultDuration) {
    let span = parseOpenDateSpan(raw, dateEnv);
    let { range } = span;
    if (!range.start) {
      return null;
    }
    if (!range.end) {
      if (defaultDuration == null) {
        return null;
      }
      range.end = dateEnv.add(range.start, defaultDuration);
    }
    return span;
  }
  function parseOpenDateSpan(raw, dateEnv) {
    let { refined: standardProps, extra } = refineProps(raw, STANDARD_PROPS);
    let startMeta = standardProps.start ? dateEnv.createMarkerMeta(standardProps.start) : null;
    let endMeta = standardProps.end ? dateEnv.createMarkerMeta(standardProps.end) : null;
    let { allDay } = standardProps;
    if (allDay == null) {
      allDay = startMeta && startMeta.isTimeUnspecified && (!endMeta || endMeta.isTimeUnspecified);
    }
    return Object.assign({ range: {
      start: startMeta ? startMeta.marker : null,
      end: endMeta ? endMeta.marker : null
    }, allDay }, extra);
  }
  function buildDateSpanApi(span, dateEnv) {
    return Object.assign(Object.assign({}, buildRangeApi(span.range, dateEnv, span.allDay)), { allDay: span.allDay });
  }
  function buildRangeApiWithTimeZone(range, dateEnv, omitTime) {
    return Object.assign(Object.assign({}, buildRangeApi(range, dateEnv, omitTime)), { timeZone: dateEnv.timeZone });
  }
  function buildRangeApi(range, dateEnv, omitTime) {
    return {
      start: dateEnv.toDate(range.start),
      end: dateEnv.toDate(range.end),
      startStr: dateEnv.formatIso(range.start, { omitTime }),
      endStr: dateEnv.formatIso(range.end, { omitTime })
    };
  }
  function fabricateEventRange(dateSpan, eventUiBases, context) {
    let res = refineEventDef({ editable: false }, context);
    let def = parseEventDef(
      res.refined,
      res.extra,
      "",
      dateSpan.allDay,
      true,
      context
    );
    return {
      def,
      ui: compileEventUi(def, eventUiBases),
      instance: createEventInstance(def.defId, dateSpan.range),
      range: dateSpan.range,
      isStart: true,
      isEnd: true
    };
  }
  function unpromisify(func, normalizedSuccessCallback, normalizedFailureCallback) {
    let isResolved = false;
    let wrappedSuccess = function(res2) {
      if (!isResolved) {
        isResolved = true;
        normalizedSuccessCallback(res2);
      }
    };
    let wrappedFailure = function(error) {
      if (!isResolved) {
        isResolved = true;
        normalizedFailureCallback(error);
      }
    };
    let res = func(wrappedSuccess, wrappedFailure);
    if (res && typeof res.then === "function") {
      res.then(wrappedSuccess, wrappedFailure);
    }
  }
  var JsonRequestError = class extends Error {
    constructor(message, response) {
      super(message);
      this.response = response;
    }
  };
  function requestJson(method, url, params) {
    method = method.toUpperCase();
    const fetchOptions = {
      method
    };
    if (method === "GET") {
      url += (url.indexOf("?") === -1 ? "?" : "&") + new URLSearchParams(params);
    } else {
      fetchOptions.body = new URLSearchParams(params);
      fetchOptions.headers = {
        "Content-Type": "application/x-www-form-urlencoded"
      };
    }
    return fetch(url, fetchOptions).then((fetchRes) => {
      if (fetchRes.ok) {
        return fetchRes.json().then((parsedResponse) => {
          return [parsedResponse, fetchRes];
        }, () => {
          throw new JsonRequestError("Failure parsing JSON", fetchRes);
        });
      } else {
        throw new JsonRequestError("Request failed", fetchRes);
      }
    });
  }
  var canVGrowWithinCell;
  function getCanVGrowWithinCell() {
    if (canVGrowWithinCell == null) {
      canVGrowWithinCell = computeCanVGrowWithinCell();
    }
    return canVGrowWithinCell;
  }
  function computeCanVGrowWithinCell() {
    if (typeof document === "undefined") {
      return true;
    }
    let el = document.createElement("div");
    el.style.position = "absolute";
    el.style.top = "0px";
    el.style.left = "0px";
    el.innerHTML = "<table><tr><td><div></div></td></tr></table>";
    el.querySelector("table").style.height = "100px";
    el.querySelector("div").style.height = "100%";
    document.body.appendChild(el);
    let div = el.querySelector("div");
    let possible = div.offsetHeight > 0;
    document.body.removeChild(el);
    return possible;
  }
  var CalendarRoot = class extends BaseComponent {
    constructor() {
      super(...arguments);
      this.state = {
        forPrint: false
      };
      this.handleBeforePrint = () => {
        flushSync(() => {
          this.setState({ forPrint: true });
        });
      };
      this.handleAfterPrint = () => {
        flushSync(() => {
          this.setState({ forPrint: false });
        });
      };
    }
    render() {
      let { props } = this;
      let { options } = props;
      let { forPrint } = this.state;
      let isHeightAuto = forPrint || options.height === "auto" || options.contentHeight === "auto";
      let height = !isHeightAuto && options.height != null ? options.height : "";
      let classNames = [
        "fc",
        forPrint ? "fc-media-print" : "fc-media-screen",
        `fc-direction-${options.direction}`,
        props.theme.getClass("root")
      ];
      if (!getCanVGrowWithinCell()) {
        classNames.push("fc-liquid-hack");
      }
      return props.children(classNames, height, isHeightAuto, forPrint);
    }
    componentDidMount() {
      let { emitter } = this.props;
      emitter.on("_beforeprint", this.handleBeforePrint);
      emitter.on("_afterprint", this.handleAfterPrint);
    }
    componentWillUnmount() {
      let { emitter } = this.props;
      emitter.off("_beforeprint", this.handleBeforePrint);
      emitter.off("_afterprint", this.handleAfterPrint);
    }
  };
  var Interaction = class {
    constructor(settings) {
      this.component = settings.component;
      this.isHitComboAllowed = settings.isHitComboAllowed || null;
    }
    destroy() {
    }
  };
  function parseInteractionSettings(component, input) {
    return {
      component,
      el: input.el,
      useEventCenter: input.useEventCenter != null ? input.useEventCenter : true,
      isHitComboAllowed: input.isHitComboAllowed || null
    };
  }
  var interactionSettingsStore = {};
  var NowTimer = class extends x {
    constructor(props, context) {
      super(props, context);
      this.handleRefresh = () => {
        let timing = this.computeTiming();
        if (timing.state.nowDate.valueOf() !== this.state.nowDate.valueOf()) {
          this.setState(timing.state);
        }
        this.clearTimeout();
        this.setTimeout(timing.waitMs);
      };
      this.handleVisibilityChange = () => {
        if (!document.hidden) {
          this.handleRefresh();
        }
      };
      this.state = this.computeTiming().state;
    }
    render() {
      let { props, state } = this;
      return props.children(state.nowDate, state.todayRange);
    }
    componentDidMount() {
      this.setTimeout();
      this.context.nowManager.addResetListener(this.handleRefresh);
      document.addEventListener("visibilitychange", this.handleVisibilityChange);
    }
    componentDidUpdate(prevProps) {
      if (prevProps.unit !== this.props.unit) {
        this.clearTimeout();
        this.setTimeout();
      }
    }
    componentWillUnmount() {
      this.clearTimeout();
      this.context.nowManager.removeResetListener(this.handleRefresh);
      document.removeEventListener("visibilitychange", this.handleVisibilityChange);
    }
    computeTiming() {
      let { props, context } = this;
      let unroundedNow = context.nowManager.getDateMarker();
      let currentUnitStart = context.dateEnv.startOf(unroundedNow, props.unit);
      let nextUnitStart = context.dateEnv.add(currentUnitStart, createDuration(1, props.unit));
      let waitMs = nextUnitStart.valueOf() - unroundedNow.valueOf();
      waitMs = Math.min(1e3 * 60 * 60 * 24, waitMs);
      return {
        state: { nowDate: currentUnitStart, todayRange: buildDayRange(currentUnitStart) },
        waitMs
      };
    }
    setTimeout(waitMs = this.computeTiming().waitMs) {
      this.timeoutId = setTimeout(() => {
        const timing = this.computeTiming();
        this.setState(timing.state, () => {
          this.setTimeout(timing.waitMs);
        });
      }, waitMs);
    }
    clearTimeout() {
      if (this.timeoutId) {
        clearTimeout(this.timeoutId);
      }
    }
  };
  NowTimer.contextType = ViewContextType;
  function buildDayRange(date) {
    let start = startOfDay(date);
    let end = addDays(start, 1);
    return { start, end };
  }
  var CalendarImpl = class {
    getCurrentData() {
      return this.currentDataManager.getCurrentData();
    }
    dispatch(action) {
      this.currentDataManager.dispatch(action);
    }
    get view() {
      return this.getCurrentData().viewApi;
    }
    batchRendering(callback) {
      callback();
    }
    updateSize() {
      this.trigger("_resize", true);
    }
    setOption(name, val) {
      this.dispatch({
        type: "SET_OPTION",
        optionName: name,
        rawOptionValue: val
      });
    }
    getOption(name) {
      return this.currentDataManager.currentCalendarOptionsInput[name];
    }
    getAvailableLocaleCodes() {
      return Object.keys(this.getCurrentData().availableRawLocales);
    }
    on(handlerName, handler) {
      let { currentDataManager } = this;
      if (currentDataManager.currentCalendarOptionsRefiners[handlerName]) {
        currentDataManager.emitter.on(handlerName, handler);
      } else {
        console.warn(`Unknown listener name '${handlerName}'`);
      }
    }
    off(handlerName, handler) {
      this.currentDataManager.emitter.off(handlerName, handler);
    }
    trigger(handlerName, ...args) {
      this.currentDataManager.emitter.trigger(handlerName, ...args);
    }
    changeView(viewType, dateOrRange) {
      this.batchRendering(() => {
        this.unselect();
        if (dateOrRange) {
          if (dateOrRange.start && dateOrRange.end) {
            this.dispatch({
              type: "CHANGE_VIEW_TYPE",
              viewType
            });
            this.dispatch({
              type: "SET_OPTION",
              optionName: "visibleRange",
              rawOptionValue: dateOrRange
            });
          } else {
            let { dateEnv } = this.getCurrentData();
            this.dispatch({
              type: "CHANGE_VIEW_TYPE",
              viewType,
              dateMarker: dateEnv.createMarker(dateOrRange)
            });
          }
        } else {
          this.dispatch({
            type: "CHANGE_VIEW_TYPE",
            viewType
          });
        }
      });
    }
    zoomTo(dateMarker, viewType) {
      let state = this.getCurrentData();
      let spec;
      viewType = viewType || "day";
      spec = state.viewSpecs[viewType] || this.getUnitViewSpec(viewType);
      this.unselect();
      if (spec) {
        this.dispatch({
          type: "CHANGE_VIEW_TYPE",
          viewType: spec.type,
          dateMarker
        });
      } else {
        this.dispatch({
          type: "CHANGE_DATE",
          dateMarker
        });
      }
    }
    getUnitViewSpec(unit) {
      let { viewSpecs, toolbarConfig } = this.getCurrentData();
      let viewTypes = [].concat(toolbarConfig.header ? toolbarConfig.header.viewsWithButtons : [], toolbarConfig.footer ? toolbarConfig.footer.viewsWithButtons : []);
      let i3;
      let spec;
      for (let viewType in viewSpecs) {
        viewTypes.push(viewType);
      }
      for (i3 = 0; i3 < viewTypes.length; i3 += 1) {
        spec = viewSpecs[viewTypes[i3]];
        if (spec) {
          if (spec.singleUnit === unit) {
            return spec;
          }
        }
      }
      return null;
    }
    prev() {
      this.unselect();
      this.dispatch({ type: "PREV" });
    }
    next() {
      this.unselect();
      this.dispatch({ type: "NEXT" });
    }
    prevYear() {
      let state = this.getCurrentData();
      this.unselect();
      this.dispatch({
        type: "CHANGE_DATE",
        dateMarker: state.dateEnv.addYears(state.currentDate, -1)
      });
    }
    nextYear() {
      let state = this.getCurrentData();
      this.unselect();
      this.dispatch({
        type: "CHANGE_DATE",
        dateMarker: state.dateEnv.addYears(state.currentDate, 1)
      });
    }
    today() {
      let state = this.getCurrentData();
      this.unselect();
      this.dispatch({
        type: "CHANGE_DATE",
        dateMarker: state.nowManager.getDateMarker()
      });
    }
    gotoDate(zonedDateInput) {
      let state = this.getCurrentData();
      this.unselect();
      this.dispatch({
        type: "CHANGE_DATE",
        dateMarker: state.dateEnv.createMarker(zonedDateInput)
      });
    }
    incrementDate(deltaInput) {
      let state = this.getCurrentData();
      let delta = createDuration(deltaInput);
      if (delta) {
        this.unselect();
        this.dispatch({
          type: "CHANGE_DATE",
          dateMarker: state.dateEnv.add(state.currentDate, delta)
        });
      }
    }
    getDate() {
      let state = this.getCurrentData();
      return state.dateEnv.toDate(state.currentDate);
    }
    formatDate(d2, formatter) {
      let { dateEnv } = this.getCurrentData();
      return dateEnv.format(dateEnv.createMarker(d2), createFormatter(formatter));
    }
    formatRange(d0, d1, settings) {
      let { dateEnv } = this.getCurrentData();
      return dateEnv.formatRange(dateEnv.createMarker(d0), dateEnv.createMarker(d1), createFormatter(settings), settings);
    }
    formatIso(d2, omitTime) {
      let { dateEnv } = this.getCurrentData();
      return dateEnv.formatIso(dateEnv.createMarker(d2), { omitTime });
    }
    select(dateOrObj, endDate) {
      let selectionInput;
      if (endDate == null) {
        if (dateOrObj.start != null) {
          selectionInput = dateOrObj;
        } else {
          selectionInput = {
            start: dateOrObj,
            end: null
          };
        }
      } else {
        selectionInput = {
          start: dateOrObj,
          end: endDate
        };
      }
      let state = this.getCurrentData();
      let selection = parseDateSpan(selectionInput, state.dateEnv, createDuration({ days: 1 }));
      if (selection) {
        this.dispatch({ type: "SELECT_DATES", selection });
        triggerDateSelect(selection, null, state);
      }
    }
    unselect(pev) {
      let state = this.getCurrentData();
      if (state.dateSelection) {
        this.dispatch({ type: "UNSELECT_DATES" });
        triggerDateUnselect(pev, state);
      }
    }
    addEvent(eventInput, sourceInput) {
      if (eventInput instanceof EventImpl) {
        let def = eventInput._def;
        let instance = eventInput._instance;
        let currentData = this.getCurrentData();
        if (!currentData.eventStore.defs[def.defId]) {
          this.dispatch({
            type: "ADD_EVENTS",
            eventStore: eventTupleToStore({ def, instance })
          });
          this.triggerEventAdd(eventInput);
        }
        return eventInput;
      }
      let state = this.getCurrentData();
      let eventSource;
      if (sourceInput instanceof EventSourceImpl) {
        eventSource = sourceInput.internalEventSource;
      } else if (typeof sourceInput === "boolean") {
        if (sourceInput) {
          [eventSource] = hashValuesToArray(state.eventSources);
        }
      } else if (sourceInput != null) {
        let sourceApi = this.getEventSourceById(sourceInput);
        if (!sourceApi) {
          console.warn(`Could not find an event source with ID "${sourceInput}"`);
          return null;
        }
        eventSource = sourceApi.internalEventSource;
      }
      let tuple = parseEvent(eventInput, eventSource, state, false);
      if (tuple) {
        let newEventApi = new EventImpl(state, tuple.def, tuple.def.recurringDef ? null : tuple.instance);
        this.dispatch({
          type: "ADD_EVENTS",
          eventStore: eventTupleToStore(tuple)
        });
        this.triggerEventAdd(newEventApi);
        return newEventApi;
      }
      return null;
    }
    triggerEventAdd(eventApi) {
      let { emitter } = this.getCurrentData();
      emitter.trigger("eventAdd", {
        event: eventApi,
        relatedEvents: [],
        revert: () => {
          this.dispatch({
            type: "REMOVE_EVENTS",
            eventStore: eventApiToStore(eventApi)
          });
        }
      });
    }
    getEventById(id) {
      let state = this.getCurrentData();
      let { defs, instances } = state.eventStore;
      id = String(id);
      for (let defId in defs) {
        let def = defs[defId];
        if (def.publicId === id) {
          if (def.recurringDef) {
            return new EventImpl(state, def, null);
          }
          for (let instanceId in instances) {
            let instance = instances[instanceId];
            if (instance.defId === def.defId) {
              return new EventImpl(state, def, instance);
            }
          }
        }
      }
      return null;
    }
    getEvents() {
      let currentData = this.getCurrentData();
      return buildEventApis(currentData.eventStore, currentData);
    }
    removeAllEvents() {
      this.dispatch({ type: "REMOVE_ALL_EVENTS" });
    }
    getEventSources() {
      let state = this.getCurrentData();
      let sourceHash = state.eventSources;
      let sourceApis = [];
      for (let internalId in sourceHash) {
        sourceApis.push(new EventSourceImpl(state, sourceHash[internalId]));
      }
      return sourceApis;
    }
    getEventSourceById(id) {
      let state = this.getCurrentData();
      let sourceHash = state.eventSources;
      id = String(id);
      for (let sourceId in sourceHash) {
        if (sourceHash[sourceId].publicId === id) {
          return new EventSourceImpl(state, sourceHash[sourceId]);
        }
      }
      return null;
    }
    addEventSource(sourceInput) {
      let state = this.getCurrentData();
      if (sourceInput instanceof EventSourceImpl) {
        if (!state.eventSources[sourceInput.internalEventSource.sourceId]) {
          this.dispatch({
            type: "ADD_EVENT_SOURCES",
            sources: [sourceInput.internalEventSource]
          });
        }
        return sourceInput;
      }
      let eventSource = parseEventSource(sourceInput, state);
      if (eventSource) {
        this.dispatch({ type: "ADD_EVENT_SOURCES", sources: [eventSource] });
        return new EventSourceImpl(state, eventSource);
      }
      return null;
    }
    removeAllEventSources() {
      this.dispatch({ type: "REMOVE_ALL_EVENT_SOURCES" });
    }
    refetchEvents() {
      this.dispatch({ type: "FETCH_EVENT_SOURCES", isRefetch: true });
    }
    scrollToTime(timeInput) {
      let time = createDuration(timeInput);
      if (time) {
        this.trigger("_scrollRequest", { time });
      }
    }
  };
  function intersectRects(rect1, rect2) {
    let res = {
      left: Math.max(rect1.left, rect2.left),
      right: Math.min(rect1.right, rect2.right),
      top: Math.max(rect1.top, rect2.top),
      bottom: Math.min(rect1.bottom, rect2.bottom)
    };
    if (res.left < res.right && res.top < res.bottom) {
      return res;
    }
    return false;
  }
  var EMPTY_EVENT_STORE = createEmptyEventStore();
  var Splitter = class {
    constructor() {
      this.getKeysForEventDefs = memoize(this._getKeysForEventDefs);
      this.splitDateSelection = memoize(this._splitDateSpan);
      this.splitEventStore = memoize(this._splitEventStore);
      this.splitIndividualUi = memoize(this._splitIndividualUi);
      this.splitEventDrag = memoize(this._splitInteraction);
      this.splitEventResize = memoize(this._splitInteraction);
      this.eventUiBuilders = {};
    }
    splitProps(props) {
      let keyInfos = this.getKeyInfo(props);
      let defKeys = this.getKeysForEventDefs(props.eventStore);
      let dateSelections = this.splitDateSelection(props.dateSelection);
      let individualUi = this.splitIndividualUi(props.eventUiBases, defKeys);
      let eventStores = this.splitEventStore(props.eventStore, defKeys);
      let eventDrags = this.splitEventDrag(props.eventDrag);
      let eventResizes = this.splitEventResize(props.eventResize);
      let splitProps = {};
      this.eventUiBuilders = mapHash(keyInfos, (info, key) => this.eventUiBuilders[key] || memoize(buildEventUiForKey));
      for (let key in keyInfos) {
        let keyInfo = keyInfos[key];
        let eventStore = eventStores[key] || EMPTY_EVENT_STORE;
        let buildEventUi = this.eventUiBuilders[key];
        splitProps[key] = {
          businessHours: keyInfo.businessHours || props.businessHours,
          dateSelection: dateSelections[key] || null,
          eventStore,
          eventUiBases: buildEventUi(props.eventUiBases[""], keyInfo.ui, individualUi[key]),
          eventSelection: eventStore.instances[props.eventSelection] ? props.eventSelection : "",
          eventDrag: eventDrags[key] || null,
          eventResize: eventResizes[key] || null
        };
      }
      return splitProps;
    }
    _splitDateSpan(dateSpan) {
      let dateSpans = {};
      if (dateSpan) {
        let keys = this.getKeysForDateSpan(dateSpan);
        for (let key of keys) {
          dateSpans[key] = dateSpan;
        }
      }
      return dateSpans;
    }
    _getKeysForEventDefs(eventStore) {
      return mapHash(eventStore.defs, (eventDef) => this.getKeysForEventDef(eventDef));
    }
    _splitEventStore(eventStore, defKeys) {
      let { defs, instances } = eventStore;
      let splitStores = {};
      for (let defId in defs) {
        for (let key of defKeys[defId]) {
          if (!splitStores[key]) {
            splitStores[key] = createEmptyEventStore();
          }
          splitStores[key].defs[defId] = defs[defId];
        }
      }
      for (let instanceId in instances) {
        let instance = instances[instanceId];
        for (let key of defKeys[instance.defId]) {
          if (splitStores[key]) {
            splitStores[key].instances[instanceId] = instance;
          }
        }
      }
      return splitStores;
    }
    _splitIndividualUi(eventUiBases, defKeys) {
      let splitHashes = {};
      for (let defId in eventUiBases) {
        if (defId) {
          for (let key of defKeys[defId]) {
            if (!splitHashes[key]) {
              splitHashes[key] = {};
            }
            splitHashes[key][defId] = eventUiBases[defId];
          }
        }
      }
      return splitHashes;
    }
    _splitInteraction(interaction) {
      let splitStates = {};
      if (interaction) {
        let affectedStores = this._splitEventStore(interaction.affectedEvents, this._getKeysForEventDefs(interaction.affectedEvents));
        let mutatedKeysByDefId = this._getKeysForEventDefs(interaction.mutatedEvents);
        let mutatedStores = this._splitEventStore(interaction.mutatedEvents, mutatedKeysByDefId);
        let populate = (key) => {
          if (!splitStates[key]) {
            splitStates[key] = {
              affectedEvents: affectedStores[key] || EMPTY_EVENT_STORE,
              mutatedEvents: mutatedStores[key] || EMPTY_EVENT_STORE,
              isEvent: interaction.isEvent
            };
          }
        };
        for (let key in affectedStores) {
          populate(key);
        }
        for (let key in mutatedStores) {
          populate(key);
        }
      }
      return splitStates;
    }
  };
  function buildEventUiForKey(allUi, eventUiForKey, individualUi) {
    let baseParts = [];
    if (allUi) {
      baseParts.push(allUi);
    }
    if (eventUiForKey) {
      baseParts.push(eventUiForKey);
    }
    let stuff = {
      "": combineEventUis(baseParts)
    };
    if (individualUi) {
      Object.assign(stuff, individualUi);
    }
    return stuff;
  }
  function getDateMeta(date, todayRange, nowDate, dateProfile) {
    return {
      dow: date.getUTCDay(),
      isDisabled: Boolean(dateProfile && (!dateProfile.activeRange || !rangeContainsMarker(dateProfile.activeRange, date))),
      isOther: Boolean(dateProfile && !rangeContainsMarker(dateProfile.currentRange, date)),
      isToday: Boolean(todayRange && rangeContainsMarker(todayRange, date)),
      isPast: Boolean(nowDate ? date < nowDate : todayRange ? date < todayRange.start : false),
      isFuture: Boolean(nowDate ? date > nowDate : todayRange ? date >= todayRange.end : false)
    };
  }
  function getDayClassNames(meta, theme) {
    let classNames = [
      "fc-day",
      `fc-day-${DAY_IDS[meta.dow]}`
    ];
    if (meta.isDisabled) {
      classNames.push("fc-day-disabled");
    } else {
      if (meta.isToday) {
        classNames.push("fc-day-today");
        classNames.push(theme.getClass("today"));
      }
      if (meta.isPast) {
        classNames.push("fc-day-past");
      }
      if (meta.isFuture) {
        classNames.push("fc-day-future");
      }
      if (meta.isOther) {
        classNames.push("fc-day-other");
      }
    }
    return classNames;
  }
  var DAY_FORMAT = createFormatter({ year: "numeric", month: "long", day: "numeric" });
  var WEEK_FORMAT = createFormatter({ week: "long" });
  function buildNavLinkAttrs(context, dateMarker, viewType = "day", isTabbable = true) {
    const { dateEnv, options, calendarApi } = context;
    let dateStr = dateEnv.format(dateMarker, viewType === "week" ? WEEK_FORMAT : DAY_FORMAT);
    if (options.navLinks) {
      let zonedDate = dateEnv.toDate(dateMarker);
      const handleInteraction = (ev) => {
        let customAction = viewType === "day" ? options.navLinkDayClick : viewType === "week" ? options.navLinkWeekClick : null;
        if (typeof customAction === "function") {
          customAction.call(calendarApi, dateEnv.toDate(dateMarker), ev);
        } else {
          if (typeof customAction === "string") {
            viewType = customAction;
          }
          calendarApi.zoomTo(dateMarker, viewType);
        }
      };
      return Object.assign({ title: formatWithOrdinals(options.navLinkHint, [dateStr, zonedDate], dateStr), "data-navlink": "" }, isTabbable ? createAriaClickAttrs(handleInteraction) : { onClick: handleInteraction });
    }
    return { "aria-label": dateStr };
  }
  var _scrollbarWidths;
  function getScrollbarWidths() {
    if (!_scrollbarWidths) {
      _scrollbarWidths = computeScrollbarWidths();
    }
    return _scrollbarWidths;
  }
  function computeScrollbarWidths() {
    let el = document.createElement("div");
    el.style.overflow = "scroll";
    el.style.position = "absolute";
    el.style.top = "-9999px";
    el.style.left = "-9999px";
    document.body.appendChild(el);
    let res = computeScrollbarWidthsForEl(el);
    document.body.removeChild(el);
    return res;
  }
  function computeScrollbarWidthsForEl(el) {
    return {
      x: el.offsetHeight - el.clientHeight,
      y: el.offsetWidth - el.clientWidth
    };
  }
  function computeClippedClientRect(el) {
    let clippingParents = getClippingParents(el);
    let rect = el.getBoundingClientRect();
    for (let clippingParent of clippingParents) {
      let intersection = intersectRects(rect, clippingParent.getBoundingClientRect());
      if (intersection) {
        rect = intersection;
      } else {
        return null;
      }
    }
    return rect;
  }
  function getClippingParents(el) {
    let parents = [];
    while (el instanceof HTMLElement) {
      let computedStyle = window.getComputedStyle(el);
      if (computedStyle.position === "fixed") {
        break;
      }
      if (/(auto|scroll)/.test(computedStyle.overflow + computedStyle.overflowY + computedStyle.overflowX)) {
        parents.push(el);
      }
      el = el.parentNode;
    }
    return parents;
  }
  var PositionCache = class {
    constructor(originEl, els, isHorizontal, isVertical) {
      this.els = els;
      let originClientRect = this.originClientRect = originEl.getBoundingClientRect();
      if (isHorizontal) {
        this.buildElHorizontals(originClientRect.left);
      }
      if (isVertical) {
        this.buildElVerticals(originClientRect.top);
      }
    }
    buildElHorizontals(originClientLeft) {
      let lefts = [];
      let rights = [];
      for (let el of this.els) {
        let rect = el.getBoundingClientRect();
        lefts.push(rect.left - originClientLeft);
        rights.push(rect.right - originClientLeft);
      }
      this.lefts = lefts;
      this.rights = rights;
    }
    buildElVerticals(originClientTop) {
      let tops = [];
      let bottoms = [];
      for (let el of this.els) {
        let rect = el.getBoundingClientRect();
        tops.push(rect.top - originClientTop);
        bottoms.push(rect.bottom - originClientTop);
      }
      this.tops = tops;
      this.bottoms = bottoms;
    }
    leftToIndex(leftPosition) {
      let { lefts, rights } = this;
      let len = lefts.length;
      let i3;
      for (i3 = 0; i3 < len; i3 += 1) {
        if (leftPosition >= lefts[i3] && leftPosition < rights[i3]) {
          return i3;
        }
      }
      return void 0;
    }
    topToIndex(topPosition) {
      let { tops, bottoms } = this;
      let len = tops.length;
      let i3;
      for (i3 = 0; i3 < len; i3 += 1) {
        if (topPosition >= tops[i3] && topPosition < bottoms[i3]) {
          return i3;
        }
      }
      return void 0;
    }
    getWidth(leftIndex) {
      return this.rights[leftIndex] - this.lefts[leftIndex];
    }
    getHeight(topIndex) {
      return this.bottoms[topIndex] - this.tops[topIndex];
    }
    similarTo(otherCache) {
      return similarNumArrays(this.tops || [], otherCache.tops || []) && similarNumArrays(this.bottoms || [], otherCache.bottoms || []) && similarNumArrays(this.lefts || [], otherCache.lefts || []) && similarNumArrays(this.rights || [], otherCache.rights || []);
    }
  };
  function similarNumArrays(a3, b3) {
    const len = a3.length;
    if (len !== b3.length) {
      return false;
    }
    for (let i3 = 0; i3 < len; i3++) {
      if (Math.round(a3[i3]) !== Math.round(b3[i3])) {
        return false;
      }
    }
    return true;
  }
  var DateComponent = class extends BaseComponent {
    constructor() {
      super(...arguments);
      this.uid = guid();
    }
    prepareHits() {
    }
    queryHit(positionLeft, positionTop, elWidth, elHeight) {
      return null;
    }
    isValidSegDownEl(el) {
      return !this.props.eventDrag && !this.props.eventResize && !elementClosest(el, ".fc-event-mirror");
    }
    isValidDateDownEl(el) {
      return !elementClosest(el, ".fc-event:not(.fc-bg-event)") && !elementClosest(el, ".fc-more-link") && !elementClosest(el, "a[data-navlink]") && !elementClosest(el, ".fc-popover");
    }
  };
  var SegHierarchy = class {
    constructor(getEntryThickness = (entry) => {
      return entry.thickness || 1;
    }) {
      this.getEntryThickness = getEntryThickness;
      this.strictOrder = false;
      this.allowReslicing = false;
      this.maxCoord = -1;
      this.maxStackCnt = -1;
      this.levelCoords = [];
      this.entriesByLevel = [];
      this.stackCnts = {};
    }
    addSegs(inputs) {
      let hiddenEntries = [];
      for (let input of inputs) {
        this.insertEntry(input, hiddenEntries);
      }
      return hiddenEntries;
    }
    insertEntry(entry, hiddenEntries) {
      let insertion = this.findInsertion(entry);
      if (this.isInsertionValid(insertion, entry)) {
        this.insertEntryAt(entry, insertion);
      } else {
        this.handleInvalidInsertion(insertion, entry, hiddenEntries);
      }
    }
    isInsertionValid(insertion, entry) {
      return (this.maxCoord === -1 || insertion.levelCoord + this.getEntryThickness(entry) <= this.maxCoord) && (this.maxStackCnt === -1 || insertion.stackCnt < this.maxStackCnt);
    }
    handleInvalidInsertion(insertion, entry, hiddenEntries) {
      if (this.allowReslicing && insertion.touchingEntry) {
        const hiddenEntry = Object.assign(Object.assign({}, entry), { span: intersectSpans(entry.span, insertion.touchingEntry.span) });
        hiddenEntries.push(hiddenEntry);
        this.splitEntry(entry, insertion.touchingEntry, hiddenEntries);
      } else {
        hiddenEntries.push(entry);
      }
    }
    splitEntry(entry, barrier, hiddenEntries) {
      let entrySpan = entry.span;
      let barrierSpan = barrier.span;
      if (entrySpan.start < barrierSpan.start) {
        this.insertEntry({
          index: entry.index,
          thickness: entry.thickness,
          span: { start: entrySpan.start, end: barrierSpan.start }
        }, hiddenEntries);
      }
      if (entrySpan.end > barrierSpan.end) {
        this.insertEntry({
          index: entry.index,
          thickness: entry.thickness,
          span: { start: barrierSpan.end, end: entrySpan.end }
        }, hiddenEntries);
      }
    }
    insertEntryAt(entry, insertion) {
      let { entriesByLevel, levelCoords } = this;
      if (insertion.lateral === -1) {
        insertAt(levelCoords, insertion.level, insertion.levelCoord);
        insertAt(entriesByLevel, insertion.level, [entry]);
      } else {
        insertAt(entriesByLevel[insertion.level], insertion.lateral, entry);
      }
      this.stackCnts[buildEntryKey(entry)] = insertion.stackCnt;
    }
    findInsertion(newEntry) {
      let { levelCoords, entriesByLevel, strictOrder, stackCnts } = this;
      let levelCnt = levelCoords.length;
      let candidateCoord = 0;
      let touchingLevel = -1;
      let touchingLateral = -1;
      let touchingEntry = null;
      let stackCnt = 0;
      for (let trackingLevel = 0; trackingLevel < levelCnt; trackingLevel += 1) {
        const trackingCoord = levelCoords[trackingLevel];
        if (!strictOrder && trackingCoord >= candidateCoord + this.getEntryThickness(newEntry)) {
          break;
        }
        let trackingEntries = entriesByLevel[trackingLevel];
        let trackingEntry;
        let searchRes = binarySearch(trackingEntries, newEntry.span.start, getEntrySpanEnd);
        let lateralIndex = searchRes[0] + searchRes[1];
        while ((trackingEntry = trackingEntries[lateralIndex]) && trackingEntry.span.start < newEntry.span.end) {
          let trackingEntryBottom = trackingCoord + this.getEntryThickness(trackingEntry);
          if (trackingEntryBottom > candidateCoord) {
            candidateCoord = trackingEntryBottom;
            touchingEntry = trackingEntry;
            touchingLevel = trackingLevel;
            touchingLateral = lateralIndex;
          }
          if (trackingEntryBottom === candidateCoord) {
            stackCnt = Math.max(stackCnt, stackCnts[buildEntryKey(trackingEntry)] + 1);
          }
          lateralIndex += 1;
        }
      }
      let destLevel = 0;
      if (touchingEntry) {
        destLevel = touchingLevel + 1;
        while (destLevel < levelCnt && levelCoords[destLevel] < candidateCoord) {
          destLevel += 1;
        }
      }
      let destLateral = -1;
      if (destLevel < levelCnt && levelCoords[destLevel] === candidateCoord) {
        destLateral = binarySearch(entriesByLevel[destLevel], newEntry.span.end, getEntrySpanEnd)[0];
      }
      return {
        touchingLevel,
        touchingLateral,
        touchingEntry,
        stackCnt,
        levelCoord: candidateCoord,
        level: destLevel,
        lateral: destLateral
      };
    }
    toRects() {
      let { entriesByLevel, levelCoords } = this;
      let levelCnt = entriesByLevel.length;
      let rects = [];
      for (let level = 0; level < levelCnt; level += 1) {
        let entries = entriesByLevel[level];
        let levelCoord = levelCoords[level];
        for (let entry of entries) {
          rects.push(Object.assign(Object.assign({}, entry), { thickness: this.getEntryThickness(entry), levelCoord }));
        }
      }
      return rects;
    }
  };
  function getEntrySpanEnd(entry) {
    return entry.span.end;
  }
  function buildEntryKey(entry) {
    return entry.index + ":" + entry.span.start;
  }
  function groupIntersectingEntries(entries) {
    let merges = [];
    for (let entry of entries) {
      let filteredMerges = [];
      let hungryMerge = {
        span: entry.span,
        entries: [entry]
      };
      for (let merge of merges) {
        if (intersectSpans(merge.span, hungryMerge.span)) {
          hungryMerge = {
            entries: merge.entries.concat(hungryMerge.entries),
            span: joinSpans(merge.span, hungryMerge.span)
          };
        } else {
          filteredMerges.push(merge);
        }
      }
      filteredMerges.push(hungryMerge);
      merges = filteredMerges;
    }
    return merges;
  }
  function joinSpans(span0, span1) {
    return {
      start: Math.min(span0.start, span1.start),
      end: Math.max(span0.end, span1.end)
    };
  }
  function intersectSpans(span0, span1) {
    let start = Math.max(span0.start, span1.start);
    let end = Math.min(span0.end, span1.end);
    if (start < end) {
      return { start, end };
    }
    return null;
  }
  function insertAt(arr, index4, item) {
    arr.splice(index4, 0, item);
  }
  function binarySearch(a3, searchVal, getItemVal) {
    let startIndex = 0;
    let endIndex = a3.length;
    if (!endIndex || searchVal < getItemVal(a3[startIndex])) {
      return [0, 0];
    }
    if (searchVal > getItemVal(a3[endIndex - 1])) {
      return [endIndex, 0];
    }
    while (startIndex < endIndex) {
      let middleIndex = Math.floor(startIndex + (endIndex - startIndex) / 2);
      let middleVal = getItemVal(a3[middleIndex]);
      if (searchVal < middleVal) {
        endIndex = middleIndex;
      } else if (searchVal > middleVal) {
        startIndex = middleIndex + 1;
      } else {
        return [middleIndex, 1];
      }
    }
    return [startIndex, 0];
  }
  function computeFallbackHeaderFormat(datesRepDistinctDays, dayCnt) {
    if (!datesRepDistinctDays || dayCnt > 10) {
      return createFormatter({ weekday: "short" });
    }
    if (dayCnt > 1) {
      return createFormatter({ weekday: "short", month: "numeric", day: "numeric", omitCommas: true });
    }
    return createFormatter({ weekday: "long" });
  }
  var CLASS_NAME = "fc-col-header-cell";
  function renderInner$1(renderProps) {
    return renderProps.text;
  }
  var TableDateCell = class extends BaseComponent {
    render() {
      let { dateEnv, options, theme, viewApi } = this.context;
      let { props } = this;
      let { date, dateProfile } = props;
      let dayMeta = getDateMeta(date, props.todayRange, null, dateProfile);
      let classNames = [CLASS_NAME].concat(getDayClassNames(dayMeta, theme));
      let text = dateEnv.format(date, props.dayHeaderFormat);
      let navLinkAttrs = !dayMeta.isDisabled && props.colCnt > 1 ? buildNavLinkAttrs(this.context, date) : {};
      let publicDate = dateEnv.toDate(date);
      if (dateEnv.namedTimeZoneImpl) {
        publicDate = addMs(publicDate, 36e5);
      }
      let renderProps = Object.assign(Object.assign(Object.assign({ date: publicDate, view: viewApi }, props.extraRenderProps), { text }), dayMeta);
      return y(ContentContainer, { elTag: "th", elClasses: classNames, elAttrs: Object.assign({ role: "columnheader", colSpan: props.colSpan, "data-date": !dayMeta.isDisabled ? formatDayString(date) : void 0 }, props.extraDataAttrs), renderProps, generatorName: "dayHeaderContent", customGenerator: options.dayHeaderContent, defaultGenerator: renderInner$1, classNameGenerator: options.dayHeaderClassNames, didMount: options.dayHeaderDidMount, willUnmount: options.dayHeaderWillUnmount }, (InnerContainer) => y("div", { className: "fc-scrollgrid-sync-inner" }, !dayMeta.isDisabled && y(InnerContainer, { elTag: "a", elAttrs: navLinkAttrs, elClasses: [
        "fc-col-header-cell-cushion",
        props.isSticky && "fc-sticky"
      ] })));
    }
  };
  var WEEKDAY_FORMAT = createFormatter({ weekday: "long" });
  var TableDowCell = class extends BaseComponent {
    render() {
      let { props } = this;
      let { dateEnv, theme, viewApi, options } = this.context;
      let date = addDays(new Date(2592e5), props.dow);
      let dateMeta = {
        dow: props.dow,
        isDisabled: false,
        isFuture: false,
        isPast: false,
        isToday: false,
        isOther: false
      };
      let text = dateEnv.format(date, props.dayHeaderFormat);
      let renderProps = Object.assign(Object.assign(Object.assign(Object.assign({
        date
      }, dateMeta), { view: viewApi }), props.extraRenderProps), { text });
      return y(ContentContainer, { elTag: "th", elClasses: [
        CLASS_NAME,
        ...getDayClassNames(dateMeta, theme),
        ...props.extraClassNames || []
      ], elAttrs: Object.assign({ role: "columnheader", colSpan: props.colSpan }, props.extraDataAttrs), renderProps, generatorName: "dayHeaderContent", customGenerator: options.dayHeaderContent, defaultGenerator: renderInner$1, classNameGenerator: options.dayHeaderClassNames, didMount: options.dayHeaderDidMount, willUnmount: options.dayHeaderWillUnmount }, (InnerContent) => y(
        "div",
        { className: "fc-scrollgrid-sync-inner" },
        y(InnerContent, { elTag: "a", elClasses: [
          "fc-col-header-cell-cushion",
          props.isSticky && "fc-sticky"
        ], elAttrs: {
          "aria-label": dateEnv.format(date, WEEKDAY_FORMAT)
        } })
      ));
    }
  };
  var DayHeader = class extends BaseComponent {
    constructor() {
      super(...arguments);
      this.createDayHeaderFormatter = memoize(createDayHeaderFormatter);
    }
    render() {
      let { context } = this;
      let { dates, dateProfile, datesRepDistinctDays, renderIntro } = this.props;
      let dayHeaderFormat = this.createDayHeaderFormatter(context.options.dayHeaderFormat, datesRepDistinctDays, dates.length);
      return y(NowTimer, { unit: "day" }, (nowDate, todayRange) => y(
        "tr",
        { role: "row" },
        renderIntro && renderIntro("day"),
        dates.map((date) => datesRepDistinctDays ? y(TableDateCell, { key: date.toISOString(), date, dateProfile, todayRange, colCnt: dates.length, dayHeaderFormat }) : y(TableDowCell, { key: date.getUTCDay(), dow: date.getUTCDay(), dayHeaderFormat }))
      ));
    }
  };
  function createDayHeaderFormatter(explicitFormat, datesRepDistinctDays, dateCnt) {
    return explicitFormat || computeFallbackHeaderFormat(datesRepDistinctDays, dateCnt);
  }
  var DaySeriesModel = class {
    constructor(range, dateProfileGenerator) {
      let date = range.start;
      let { end } = range;
      let indices = [];
      let dates = [];
      let dayIndex = -1;
      while (date < end) {
        if (dateProfileGenerator.isHiddenDay(date)) {
          indices.push(dayIndex + 0.5);
        } else {
          dayIndex += 1;
          indices.push(dayIndex);
          dates.push(date);
        }
        date = addDays(date, 1);
      }
      this.dates = dates;
      this.indices = indices;
      this.cnt = dates.length;
    }
    sliceRange(range) {
      let firstIndex = this.getDateDayIndex(range.start);
      let lastIndex = this.getDateDayIndex(addDays(range.end, -1));
      let clippedFirstIndex = Math.max(0, firstIndex);
      let clippedLastIndex = Math.min(this.cnt - 1, lastIndex);
      clippedFirstIndex = Math.ceil(clippedFirstIndex);
      clippedLastIndex = Math.floor(clippedLastIndex);
      if (clippedFirstIndex <= clippedLastIndex) {
        return {
          firstIndex: clippedFirstIndex,
          lastIndex: clippedLastIndex,
          isStart: firstIndex === clippedFirstIndex,
          isEnd: lastIndex === clippedLastIndex
        };
      }
      return null;
    }
    getDateDayIndex(date) {
      let { indices } = this;
      let dayOffset = Math.floor(diffDays(this.dates[0], date));
      if (dayOffset < 0) {
        return indices[0] - 1;
      }
      if (dayOffset >= indices.length) {
        return indices[indices.length - 1] + 1;
      }
      return indices[dayOffset];
    }
  };
  var DayTableModel = class {
    constructor(daySeries, breakOnWeeks) {
      let { dates } = daySeries;
      let daysPerRow;
      let firstDay;
      let rowCnt;
      if (breakOnWeeks) {
        firstDay = dates[0].getUTCDay();
        for (daysPerRow = 1; daysPerRow < dates.length; daysPerRow += 1) {
          if (dates[daysPerRow].getUTCDay() === firstDay) {
            break;
          }
        }
        rowCnt = Math.ceil(dates.length / daysPerRow);
      } else {
        rowCnt = 1;
        daysPerRow = dates.length;
      }
      this.rowCnt = rowCnt;
      this.colCnt = daysPerRow;
      this.daySeries = daySeries;
      this.cells = this.buildCells();
      this.headerDates = this.buildHeaderDates();
    }
    buildCells() {
      let rows = [];
      for (let row = 0; row < this.rowCnt; row += 1) {
        let cells = [];
        for (let col = 0; col < this.colCnt; col += 1) {
          cells.push(this.buildCell(row, col));
        }
        rows.push(cells);
      }
      return rows;
    }
    buildCell(row, col) {
      let date = this.daySeries.dates[row * this.colCnt + col];
      return {
        key: date.toISOString(),
        date
      };
    }
    buildHeaderDates() {
      let dates = [];
      for (let col = 0; col < this.colCnt; col += 1) {
        dates.push(this.cells[0][col].date);
      }
      return dates;
    }
    sliceRange(range) {
      let { colCnt } = this;
      let seriesSeg = this.daySeries.sliceRange(range);
      let segs = [];
      if (seriesSeg) {
        let { firstIndex, lastIndex } = seriesSeg;
        let index4 = firstIndex;
        while (index4 <= lastIndex) {
          let row = Math.floor(index4 / colCnt);
          let nextIndex = Math.min((row + 1) * colCnt, lastIndex + 1);
          segs.push({
            row,
            firstCol: index4 % colCnt,
            lastCol: (nextIndex - 1) % colCnt,
            isStart: seriesSeg.isStart && index4 === firstIndex,
            isEnd: seriesSeg.isEnd && nextIndex - 1 === lastIndex
          });
          index4 = nextIndex;
        }
      }
      return segs;
    }
  };
  var Slicer = class {
    constructor() {
      this.sliceBusinessHours = memoize(this._sliceBusinessHours);
      this.sliceDateSelection = memoize(this._sliceDateSpan);
      this.sliceEventStore = memoize(this._sliceEventStore);
      this.sliceEventDrag = memoize(this._sliceInteraction);
      this.sliceEventResize = memoize(this._sliceInteraction);
      this.forceDayIfListItem = false;
    }
    sliceProps(props, dateProfile, nextDayThreshold, context, ...extraArgs) {
      let { eventUiBases } = props;
      let eventSegs = this.sliceEventStore(props.eventStore, eventUiBases, dateProfile, nextDayThreshold, ...extraArgs);
      return {
        dateSelectionSegs: this.sliceDateSelection(props.dateSelection, dateProfile, nextDayThreshold, eventUiBases, context, ...extraArgs),
        businessHourSegs: this.sliceBusinessHours(props.businessHours, dateProfile, nextDayThreshold, context, ...extraArgs),
        fgEventSegs: eventSegs.fg,
        bgEventSegs: eventSegs.bg,
        eventDrag: this.sliceEventDrag(props.eventDrag, eventUiBases, dateProfile, nextDayThreshold, ...extraArgs),
        eventResize: this.sliceEventResize(props.eventResize, eventUiBases, dateProfile, nextDayThreshold, ...extraArgs),
        eventSelection: props.eventSelection
      };
    }
    sliceNowDate(date, dateProfile, nextDayThreshold, context, ...extraArgs) {
      return this._sliceDateSpan(
        { range: { start: date, end: addMs(date, 1) }, allDay: false },
        dateProfile,
        nextDayThreshold,
        {},
        context,
        ...extraArgs
      );
    }
    _sliceBusinessHours(businessHours, dateProfile, nextDayThreshold, context, ...extraArgs) {
      if (!businessHours) {
        return [];
      }
      return this._sliceEventStore(expandRecurring(businessHours, computeActiveRange(dateProfile, Boolean(nextDayThreshold)), context), {}, dateProfile, nextDayThreshold, ...extraArgs).bg;
    }
    _sliceEventStore(eventStore, eventUiBases, dateProfile, nextDayThreshold, ...extraArgs) {
      if (eventStore) {
        let rangeRes = sliceEventStore(eventStore, eventUiBases, computeActiveRange(dateProfile, Boolean(nextDayThreshold)), nextDayThreshold);
        return {
          bg: this.sliceEventRanges(rangeRes.bg, extraArgs),
          fg: this.sliceEventRanges(rangeRes.fg, extraArgs)
        };
      }
      return { bg: [], fg: [] };
    }
    _sliceInteraction(interaction, eventUiBases, dateProfile, nextDayThreshold, ...extraArgs) {
      if (!interaction) {
        return null;
      }
      let rangeRes = sliceEventStore(interaction.mutatedEvents, eventUiBases, computeActiveRange(dateProfile, Boolean(nextDayThreshold)), nextDayThreshold);
      return {
        segs: this.sliceEventRanges(rangeRes.fg, extraArgs),
        affectedInstances: interaction.affectedEvents.instances,
        isEvent: interaction.isEvent
      };
    }
    _sliceDateSpan(dateSpan, dateProfile, nextDayThreshold, eventUiBases, context, ...extraArgs) {
      if (!dateSpan) {
        return [];
      }
      let activeRange = computeActiveRange(dateProfile, Boolean(nextDayThreshold));
      let activeDateSpanRange = intersectRanges(dateSpan.range, activeRange);
      if (activeDateSpanRange) {
        dateSpan = Object.assign(Object.assign({}, dateSpan), { range: activeDateSpanRange });
        let eventRange = fabricateEventRange(dateSpan, eventUiBases, context);
        let segs = this.sliceRange(dateSpan.range, ...extraArgs);
        for (let seg of segs) {
          seg.eventRange = eventRange;
        }
        return segs;
      }
      return [];
    }
    sliceEventRanges(eventRanges, extraArgs) {
      let segs = [];
      for (let eventRange of eventRanges) {
        segs.push(...this.sliceEventRange(eventRange, extraArgs));
      }
      return segs;
    }
    sliceEventRange(eventRange, extraArgs) {
      let dateRange = eventRange.range;
      if (this.forceDayIfListItem && eventRange.ui.display === "list-item") {
        dateRange = {
          start: dateRange.start,
          end: addDays(dateRange.start, 1)
        };
      }
      let segs = this.sliceRange(dateRange, ...extraArgs);
      for (let seg of segs) {
        seg.eventRange = eventRange;
        seg.isStart = eventRange.isStart && seg.isStart;
        seg.isEnd = eventRange.isEnd && seg.isEnd;
      }
      return segs;
    }
  };
  function computeActiveRange(dateProfile, isComponentAllDay) {
    let range = dateProfile.activeRange;
    if (isComponentAllDay) {
      return range;
    }
    return {
      start: addMs(range.start, dateProfile.slotMinTime.milliseconds),
      end: addMs(range.end, dateProfile.slotMaxTime.milliseconds - 864e5)
    };
  }
  var VISIBLE_HIDDEN_RE = /^(visible|hidden)$/;
  var Scroller = class extends BaseComponent {
    constructor() {
      super(...arguments);
      this.handleEl = (el) => {
        this.el = el;
        setRef(this.props.elRef, el);
      };
    }
    render() {
      let { props } = this;
      let { liquid, liquidIsAbsolute } = props;
      let isAbsolute = liquid && liquidIsAbsolute;
      let className = ["fc-scroller"];
      if (liquid) {
        if (liquidIsAbsolute) {
          className.push("fc-scroller-liquid-absolute");
        } else {
          className.push("fc-scroller-liquid");
        }
      }
      return y("div", { ref: this.handleEl, className: className.join(" "), style: {
        overflowX: props.overflowX,
        overflowY: props.overflowY,
        left: isAbsolute && -(props.overcomeLeft || 0) || "",
        right: isAbsolute && -(props.overcomeRight || 0) || "",
        bottom: isAbsolute && -(props.overcomeBottom || 0) || "",
        marginLeft: !isAbsolute && -(props.overcomeLeft || 0) || "",
        marginRight: !isAbsolute && -(props.overcomeRight || 0) || "",
        marginBottom: !isAbsolute && -(props.overcomeBottom || 0) || "",
        maxHeight: props.maxHeight || ""
      } }, props.children);
    }
    needsXScrolling() {
      if (VISIBLE_HIDDEN_RE.test(this.props.overflowX)) {
        return false;
      }
      let { el } = this;
      let realClientWidth = this.el.getBoundingClientRect().width - this.getYScrollbarWidth();
      let { children } = el;
      for (let i3 = 0; i3 < children.length; i3 += 1) {
        let childEl = children[i3];
        if (childEl.getBoundingClientRect().width > realClientWidth) {
          return true;
        }
      }
      return false;
    }
    needsYScrolling() {
      if (VISIBLE_HIDDEN_RE.test(this.props.overflowY)) {
        return false;
      }
      let { el } = this;
      let realClientHeight = this.el.getBoundingClientRect().height - this.getXScrollbarWidth();
      let { children } = el;
      for (let i3 = 0; i3 < children.length; i3 += 1) {
        let childEl = children[i3];
        if (childEl.getBoundingClientRect().height > realClientHeight) {
          return true;
        }
      }
      return false;
    }
    getXScrollbarWidth() {
      if (VISIBLE_HIDDEN_RE.test(this.props.overflowX)) {
        return 0;
      }
      return this.el.offsetHeight - this.el.clientHeight;
    }
    getYScrollbarWidth() {
      if (VISIBLE_HIDDEN_RE.test(this.props.overflowY)) {
        return 0;
      }
      return this.el.offsetWidth - this.el.clientWidth;
    }
  };
  var RefMap = class {
    constructor(masterCallback) {
      this.masterCallback = masterCallback;
      this.currentMap = {};
      this.depths = {};
      this.callbackMap = {};
      this.handleValue = (val, key) => {
        let { depths, currentMap } = this;
        let removed = false;
        let added = false;
        if (val !== null) {
          removed = key in currentMap;
          currentMap[key] = val;
          depths[key] = (depths[key] || 0) + 1;
          added = true;
        } else {
          depths[key] -= 1;
          if (!depths[key]) {
            delete currentMap[key];
            delete this.callbackMap[key];
            removed = true;
          }
        }
        if (this.masterCallback) {
          if (removed) {
            this.masterCallback(null, String(key));
          }
          if (added) {
            this.masterCallback(val, String(key));
          }
        }
      };
    }
    createRef(key) {
      let refCallback = this.callbackMap[key];
      if (!refCallback) {
        refCallback = this.callbackMap[key] = (val) => {
          this.handleValue(val, String(key));
        };
      }
      return refCallback;
    }
    collect(startIndex, endIndex, step) {
      return collectFromHash(this.currentMap, startIndex, endIndex, step);
    }
    getAll() {
      return hashValuesToArray(this.currentMap);
    }
  };
  function computeShrinkWidth(chunkEls) {
    let shrinkCells = findElements(chunkEls, ".fc-scrollgrid-shrink");
    let largestWidth = 0;
    for (let shrinkCell of shrinkCells) {
      largestWidth = Math.max(largestWidth, computeSmallestCellWidth(shrinkCell));
    }
    return Math.ceil(largestWidth);
  }
  function getSectionHasLiquidHeight(props, sectionConfig) {
    return props.liquid && sectionConfig.liquid;
  }
  function getAllowYScrolling(props, sectionConfig) {
    return sectionConfig.maxHeight != null || getSectionHasLiquidHeight(props, sectionConfig);
  }
  function renderChunkContent(sectionConfig, chunkConfig, arg, isHeader) {
    let { expandRows } = arg;
    let content = typeof chunkConfig.content === "function" ? chunkConfig.content(arg) : y("table", {
      role: "presentation",
      className: [
        chunkConfig.tableClassName,
        sectionConfig.syncRowHeights ? "fc-scrollgrid-sync-table" : ""
      ].join(" "),
      style: {
        minWidth: arg.tableMinWidth,
        width: arg.clientWidth,
        height: expandRows ? arg.clientHeight : ""
      }
    }, arg.tableColGroupNode, y(isHeader ? "thead" : "tbody", {
      role: "presentation"
    }, typeof chunkConfig.rowContent === "function" ? chunkConfig.rowContent(arg) : chunkConfig.rowContent));
    return content;
  }
  function isColPropsEqual(cols0, cols1) {
    return isArraysEqual(cols0, cols1, isPropsEqual);
  }
  function renderMicroColGroup(cols, shrinkWidth) {
    let colNodes = [];
    for (let colProps of cols) {
      let span = colProps.span || 1;
      for (let i3 = 0; i3 < span; i3 += 1) {
        colNodes.push(y("col", { style: {
          width: colProps.width === "shrink" ? sanitizeShrinkWidth(shrinkWidth) : colProps.width || "",
          minWidth: colProps.minWidth || ""
        } }));
      }
    }
    return y("colgroup", {}, ...colNodes);
  }
  function sanitizeShrinkWidth(shrinkWidth) {
    return shrinkWidth == null ? 4 : shrinkWidth;
  }
  function hasShrinkWidth(cols) {
    for (let col of cols) {
      if (col.width === "shrink") {
        return true;
      }
    }
    return false;
  }
  function getScrollGridClassNames(liquid, context) {
    let classNames = [
      "fc-scrollgrid",
      context.theme.getClass("table")
    ];
    if (liquid) {
      classNames.push("fc-scrollgrid-liquid");
    }
    return classNames;
  }
  function getSectionClassNames(sectionConfig, wholeTableVGrow) {
    let classNames = [
      "fc-scrollgrid-section",
      `fc-scrollgrid-section-${sectionConfig.type}`,
      sectionConfig.className
    ];
    if (wholeTableVGrow && sectionConfig.liquid && sectionConfig.maxHeight == null) {
      classNames.push("fc-scrollgrid-section-liquid");
    }
    if (sectionConfig.isSticky) {
      classNames.push("fc-scrollgrid-section-sticky");
    }
    return classNames;
  }
  function renderScrollShim(arg) {
    return y("div", { className: "fc-scrollgrid-sticky-shim", style: {
      width: arg.clientWidth,
      minWidth: arg.tableMinWidth
    } });
  }
  function getStickyHeaderDates(options) {
    let { stickyHeaderDates } = options;
    if (stickyHeaderDates == null || stickyHeaderDates === "auto") {
      stickyHeaderDates = options.height === "auto" || options.viewHeight === "auto";
    }
    return stickyHeaderDates;
  }
  function getStickyFooterScrollbar(options) {
    let { stickyFooterScrollbar } = options;
    if (stickyFooterScrollbar == null || stickyFooterScrollbar === "auto") {
      stickyFooterScrollbar = options.height === "auto" || options.viewHeight === "auto";
    }
    return stickyFooterScrollbar;
  }
  var SimpleScrollGrid = class extends BaseComponent {
    constructor() {
      super(...arguments);
      this.processCols = memoize((a3) => a3, isColPropsEqual);
      this.renderMicroColGroup = memoize(renderMicroColGroup);
      this.scrollerRefs = new RefMap();
      this.scrollerElRefs = new RefMap(this._handleScrollerEl.bind(this));
      this.state = {
        shrinkWidth: null,
        forceYScrollbars: false,
        scrollerClientWidths: {},
        scrollerClientHeights: {}
      };
      this.handleSizing = () => {
        this.safeSetState(Object.assign({ shrinkWidth: this.computeShrinkWidth() }, this.computeScrollerDims()));
      };
    }
    render() {
      let { props, state, context } = this;
      let sectionConfigs = props.sections || [];
      let cols = this.processCols(props.cols);
      let microColGroupNode = this.renderMicroColGroup(cols, state.shrinkWidth);
      let classNames = getScrollGridClassNames(props.liquid, context);
      if (props.collapsibleWidth) {
        classNames.push("fc-scrollgrid-collapsible");
      }
      let configCnt = sectionConfigs.length;
      let configI = 0;
      let currentConfig;
      let headSectionNodes = [];
      let bodySectionNodes = [];
      let footSectionNodes = [];
      while (configI < configCnt && (currentConfig = sectionConfigs[configI]).type === "header") {
        headSectionNodes.push(this.renderSection(currentConfig, microColGroupNode, true));
        configI += 1;
      }
      while (configI < configCnt && (currentConfig = sectionConfigs[configI]).type === "body") {
        bodySectionNodes.push(this.renderSection(currentConfig, microColGroupNode, false));
        configI += 1;
      }
      while (configI < configCnt && (currentConfig = sectionConfigs[configI]).type === "footer") {
        footSectionNodes.push(this.renderSection(currentConfig, microColGroupNode, true));
        configI += 1;
      }
      let isBuggy = !getCanVGrowWithinCell();
      const roleAttrs = { role: "rowgroup" };
      return y("table", {
        role: "grid",
        className: classNames.join(" "),
        style: { height: props.height }
      }, Boolean(!isBuggy && headSectionNodes.length) && y("thead", roleAttrs, ...headSectionNodes), Boolean(!isBuggy && bodySectionNodes.length) && y("tbody", roleAttrs, ...bodySectionNodes), Boolean(!isBuggy && footSectionNodes.length) && y("tfoot", roleAttrs, ...footSectionNodes), isBuggy && y("tbody", roleAttrs, ...headSectionNodes, ...bodySectionNodes, ...footSectionNodes));
    }
    renderSection(sectionConfig, microColGroupNode, isHeader) {
      if ("outerContent" in sectionConfig) {
        return y(_, { key: sectionConfig.key }, sectionConfig.outerContent);
      }
      return y("tr", { key: sectionConfig.key, role: "presentation", className: getSectionClassNames(sectionConfig, this.props.liquid).join(" ") }, this.renderChunkTd(sectionConfig, microColGroupNode, sectionConfig.chunk, isHeader));
    }
    renderChunkTd(sectionConfig, microColGroupNode, chunkConfig, isHeader) {
      if ("outerContent" in chunkConfig) {
        return chunkConfig.outerContent;
      }
      let { props } = this;
      let { forceYScrollbars, scrollerClientWidths, scrollerClientHeights } = this.state;
      let needsYScrolling = getAllowYScrolling(props, sectionConfig);
      let isLiquid = getSectionHasLiquidHeight(props, sectionConfig);
      let overflowY = !props.liquid ? "visible" : forceYScrollbars ? "scroll" : !needsYScrolling ? "hidden" : "auto";
      let sectionKey = sectionConfig.key;
      let content = renderChunkContent(sectionConfig, chunkConfig, {
        tableColGroupNode: microColGroupNode,
        tableMinWidth: "",
        clientWidth: !props.collapsibleWidth && scrollerClientWidths[sectionKey] !== void 0 ? scrollerClientWidths[sectionKey] : null,
        clientHeight: scrollerClientHeights[sectionKey] !== void 0 ? scrollerClientHeights[sectionKey] : null,
        expandRows: sectionConfig.expandRows,
        syncRowHeights: false,
        rowSyncHeights: [],
        reportRowHeightChange: () => {
        }
      }, isHeader);
      return y(isHeader ? "th" : "td", {
        ref: chunkConfig.elRef,
        role: "presentation"
      }, y(
        "div",
        { className: `fc-scroller-harness${isLiquid ? " fc-scroller-harness-liquid" : ""}` },
        y(Scroller, { ref: this.scrollerRefs.createRef(sectionKey), elRef: this.scrollerElRefs.createRef(sectionKey), overflowY, overflowX: !props.liquid ? "visible" : "hidden", maxHeight: sectionConfig.maxHeight, liquid: isLiquid, liquidIsAbsolute: true }, content)
      ));
    }
    _handleScrollerEl(scrollerEl, key) {
      let section = getSectionByKey(this.props.sections, key);
      if (section) {
        setRef(section.chunk.scrollerElRef, scrollerEl);
      }
    }
    componentDidMount() {
      this.handleSizing();
      this.context.addResizeHandler(this.handleSizing);
    }
    componentDidUpdate() {
      this.handleSizing();
    }
    componentWillUnmount() {
      this.context.removeResizeHandler(this.handleSizing);
    }
    computeShrinkWidth() {
      return hasShrinkWidth(this.props.cols) ? computeShrinkWidth(this.scrollerElRefs.getAll()) : 0;
    }
    computeScrollerDims() {
      let scrollbarWidth = getScrollbarWidths();
      let { scrollerRefs, scrollerElRefs } = this;
      let forceYScrollbars = false;
      let scrollerClientWidths = {};
      let scrollerClientHeights = {};
      for (let sectionKey in scrollerRefs.currentMap) {
        let scroller = scrollerRefs.currentMap[sectionKey];
        if (scroller && scroller.needsYScrolling()) {
          forceYScrollbars = true;
          break;
        }
      }
      for (let section of this.props.sections) {
        let sectionKey = section.key;
        let scrollerEl = scrollerElRefs.currentMap[sectionKey];
        if (scrollerEl) {
          let harnessEl = scrollerEl.parentNode;
          scrollerClientWidths[sectionKey] = Math.floor(harnessEl.getBoundingClientRect().width - (forceYScrollbars ? scrollbarWidth.y : 0));
          scrollerClientHeights[sectionKey] = Math.floor(harnessEl.getBoundingClientRect().height);
        }
      }
      return { forceYScrollbars, scrollerClientWidths, scrollerClientHeights };
    }
  };
  SimpleScrollGrid.addStateEquality({
    scrollerClientWidths: isPropsEqual,
    scrollerClientHeights: isPropsEqual
  });
  function getSectionByKey(sections, key) {
    for (let section of sections) {
      if (section.key === key) {
        return section;
      }
    }
    return null;
  }
  var EventContainer = class extends BaseComponent {
    constructor() {
      super(...arguments);
      this.handleEl = (el) => {
        this.el = el;
        if (el) {
          setElSeg(el, this.props.seg);
        }
      };
    }
    render() {
      const { props, context } = this;
      const { options } = context;
      const { seg } = props;
      const { eventRange } = seg;
      const { ui } = eventRange;
      const renderProps = {
        event: new EventImpl(context, eventRange.def, eventRange.instance),
        view: context.viewApi,
        timeText: props.timeText,
        textColor: ui.textColor,
        backgroundColor: ui.backgroundColor,
        borderColor: ui.borderColor,
        isDraggable: !props.disableDragging && computeSegDraggable(seg, context),
        isStartResizable: !props.disableResizing && computeSegStartResizable(seg, context),
        isEndResizable: !props.disableResizing && computeSegEndResizable(seg),
        isMirror: Boolean(props.isDragging || props.isResizing || props.isDateSelecting),
        isStart: Boolean(seg.isStart),
        isEnd: Boolean(seg.isEnd),
        isPast: Boolean(props.isPast),
        isFuture: Boolean(props.isFuture),
        isToday: Boolean(props.isToday),
        isSelected: Boolean(props.isSelected),
        isDragging: Boolean(props.isDragging),
        isResizing: Boolean(props.isResizing)
      };
      return y(ContentContainer, Object.assign({}, props, { elRef: this.handleEl, elClasses: [
        ...getEventClassNames(renderProps),
        ...seg.eventRange.ui.classNames,
        ...props.elClasses || []
      ], renderProps, generatorName: "eventContent", customGenerator: options.eventContent, defaultGenerator: props.defaultGenerator, classNameGenerator: options.eventClassNames, didMount: options.eventDidMount, willUnmount: options.eventWillUnmount }));
    }
    componentDidUpdate(prevProps) {
      if (this.el && this.props.seg !== prevProps.seg) {
        setElSeg(this.el, this.props.seg);
      }
    }
  };
  var StandardEvent = class extends BaseComponent {
    render() {
      let { props, context } = this;
      let { options } = context;
      let { seg } = props;
      let { ui } = seg.eventRange;
      let timeFormat = options.eventTimeFormat || props.defaultTimeFormat;
      let timeText = buildSegTimeText(seg, timeFormat, context, props.defaultDisplayEventTime, props.defaultDisplayEventEnd);
      return y(EventContainer, Object.assign({}, props, { elTag: "a", elStyle: {
        borderColor: ui.borderColor,
        backgroundColor: ui.backgroundColor
      }, elAttrs: getSegAnchorAttrs(seg, context), defaultGenerator: renderInnerContent$1, timeText }), (InnerContent, eventContentArg) => y(
        _,
        null,
        y(InnerContent, { elTag: "div", elClasses: ["fc-event-main"], elStyle: { color: eventContentArg.textColor } }),
        Boolean(eventContentArg.isStartResizable) && y("div", { className: "fc-event-resizer fc-event-resizer-start" }),
        Boolean(eventContentArg.isEndResizable) && y("div", { className: "fc-event-resizer fc-event-resizer-end" })
      ));
    }
  };
  function renderInnerContent$1(innerProps) {
    return y(
      "div",
      { className: "fc-event-main-frame" },
      innerProps.timeText && y("div", { className: "fc-event-time" }, innerProps.timeText),
      y(
        "div",
        { className: "fc-event-title-container" },
        y("div", { className: "fc-event-title fc-sticky" }, innerProps.event.title || y(_, null, "\xA0"))
      )
    );
  }
  var NowIndicatorContainer = (props) => y(ViewContextType.Consumer, null, (context) => {
    let { options } = context;
    let renderProps = {
      isAxis: props.isAxis,
      date: context.dateEnv.toDate(props.date),
      view: context.viewApi
    };
    return y(ContentContainer, Object.assign({}, props, { elTag: props.elTag || "div", renderProps, generatorName: "nowIndicatorContent", customGenerator: options.nowIndicatorContent, classNameGenerator: options.nowIndicatorClassNames, didMount: options.nowIndicatorDidMount, willUnmount: options.nowIndicatorWillUnmount }));
  });
  var DAY_NUM_FORMAT = createFormatter({ day: "numeric" });
  var DayCellContainer = class extends BaseComponent {
    constructor() {
      super(...arguments);
      this.refineRenderProps = memoizeObjArg(refineRenderProps);
    }
    render() {
      let { props, context } = this;
      let { options } = context;
      let renderProps = this.refineRenderProps({
        date: props.date,
        dateProfile: props.dateProfile,
        todayRange: props.todayRange,
        isMonthStart: props.isMonthStart || false,
        showDayNumber: props.showDayNumber,
        extraRenderProps: props.extraRenderProps,
        viewApi: context.viewApi,
        dateEnv: context.dateEnv,
        monthStartFormat: options.monthStartFormat
      });
      return y(ContentContainer, Object.assign({}, props, { elClasses: [
        ...getDayClassNames(renderProps, context.theme),
        ...props.elClasses || []
      ], elAttrs: Object.assign(Object.assign({}, props.elAttrs), renderProps.isDisabled ? {} : { "data-date": formatDayString(props.date) }), renderProps, generatorName: "dayCellContent", customGenerator: options.dayCellContent, defaultGenerator: props.defaultGenerator, classNameGenerator: renderProps.isDisabled ? void 0 : options.dayCellClassNames, didMount: options.dayCellDidMount, willUnmount: options.dayCellWillUnmount }));
    }
  };
  function hasCustomDayCellContent(options) {
    return Boolean(options.dayCellContent || hasCustomRenderingHandler("dayCellContent", options));
  }
  function refineRenderProps(raw) {
    let { date, dateEnv, dateProfile, isMonthStart } = raw;
    let dayMeta = getDateMeta(date, raw.todayRange, null, dateProfile);
    let dayNumberText = raw.showDayNumber ? dateEnv.format(date, isMonthStart ? raw.monthStartFormat : DAY_NUM_FORMAT) : "";
    return Object.assign(Object.assign(Object.assign({ date: dateEnv.toDate(date), view: raw.viewApi }, dayMeta), {
      isMonthStart,
      dayNumberText
    }), raw.extraRenderProps);
  }
  var BgEvent = class extends BaseComponent {
    render() {
      let { props } = this;
      let { seg } = props;
      return y(EventContainer, { elTag: "div", elClasses: ["fc-bg-event"], elStyle: { backgroundColor: seg.eventRange.ui.backgroundColor }, defaultGenerator: renderInnerContent, seg, timeText: "", isDragging: false, isResizing: false, isDateSelecting: false, isSelected: false, isPast: props.isPast, isFuture: props.isFuture, isToday: props.isToday, disableDragging: true, disableResizing: true });
    }
  };
  function renderInnerContent(props) {
    let { title } = props.event;
    return title && y("div", { className: "fc-event-title" }, props.event.title);
  }
  function renderFill(fillType) {
    return y("div", { className: `fc-${fillType}` });
  }
  var WeekNumberContainer = (props) => y(ViewContextType.Consumer, null, (context) => {
    let { dateEnv, options } = context;
    let { date } = props;
    let format = options.weekNumberFormat || props.defaultFormat;
    let num = dateEnv.computeWeekNumber(date);
    let text = dateEnv.format(date, format);
    let renderProps = { num, text, date };
    return y(
      ContentContainer,
      Object.assign({}, props, { renderProps, generatorName: "weekNumberContent", customGenerator: options.weekNumberContent, defaultGenerator: renderInner, classNameGenerator: options.weekNumberClassNames, didMount: options.weekNumberDidMount, willUnmount: options.weekNumberWillUnmount })
    );
  });
  function renderInner(innerProps) {
    return innerProps.text;
  }
  var PADDING_FROM_VIEWPORT = 10;
  var Popover = class extends BaseComponent {
    constructor() {
      super(...arguments);
      this.state = {
        titleId: getUniqueDomId()
      };
      this.handleRootEl = (el) => {
        this.rootEl = el;
        if (this.props.elRef) {
          setRef(this.props.elRef, el);
        }
      };
      this.handleDocumentMouseDown = (ev) => {
        const target = getEventTargetViaRoot(ev);
        if (!this.rootEl.contains(target)) {
          this.handleCloseClick();
        }
      };
      this.handleDocumentKeyDown = (ev) => {
        if (ev.key === "Escape") {
          this.handleCloseClick();
        }
      };
      this.handleCloseClick = () => {
        let { onClose } = this.props;
        if (onClose) {
          onClose();
        }
      };
    }
    render() {
      let { theme, options } = this.context;
      let { props, state } = this;
      let classNames = [
        "fc-popover",
        theme.getClass("popover")
      ].concat(props.extraClassNames || []);
      return j3(y(
        "div",
        Object.assign({}, props.extraAttrs, { id: props.id, className: classNames.join(" "), "aria-labelledby": state.titleId, ref: this.handleRootEl }),
        y(
          "div",
          { className: "fc-popover-header " + theme.getClass("popoverHeader") },
          y("span", { className: "fc-popover-title", id: state.titleId }, props.title),
          y("span", { className: "fc-popover-close " + theme.getIconClass("close"), title: options.closeHint, onClick: this.handleCloseClick })
        ),
        y("div", { className: "fc-popover-body " + theme.getClass("popoverContent") }, props.children)
      ), props.parentEl);
    }
    componentDidMount() {
      document.addEventListener("mousedown", this.handleDocumentMouseDown);
      document.addEventListener("keydown", this.handleDocumentKeyDown);
      this.updateSize();
    }
    componentWillUnmount() {
      document.removeEventListener("mousedown", this.handleDocumentMouseDown);
      document.removeEventListener("keydown", this.handleDocumentKeyDown);
    }
    updateSize() {
      let { isRtl } = this.context;
      let { alignmentEl, alignGridTop } = this.props;
      let { rootEl } = this;
      let alignmentRect = computeClippedClientRect(alignmentEl);
      if (alignmentRect) {
        let popoverDims = rootEl.getBoundingClientRect();
        let popoverTop = alignGridTop ? elementClosest(alignmentEl, ".fc-scrollgrid").getBoundingClientRect().top : alignmentRect.top;
        let popoverLeft = isRtl ? alignmentRect.right - popoverDims.width : alignmentRect.left;
        popoverTop = Math.max(popoverTop, PADDING_FROM_VIEWPORT);
        popoverLeft = Math.min(popoverLeft, document.documentElement.clientWidth - PADDING_FROM_VIEWPORT - popoverDims.width);
        popoverLeft = Math.max(popoverLeft, PADDING_FROM_VIEWPORT);
        let origin = rootEl.offsetParent.getBoundingClientRect();
        applyStyle(rootEl, {
          top: popoverTop - origin.top,
          left: popoverLeft - origin.left
        });
      }
    }
  };
  var MorePopover = class extends DateComponent {
    constructor() {
      super(...arguments);
      this.handleRootEl = (rootEl) => {
        this.rootEl = rootEl;
        if (rootEl) {
          this.context.registerInteractiveComponent(this, {
            el: rootEl,
            useEventCenter: false
          });
        } else {
          this.context.unregisterInteractiveComponent(this);
        }
      };
    }
    render() {
      let { options, dateEnv } = this.context;
      let { props } = this;
      let { startDate, todayRange, dateProfile } = props;
      let title = dateEnv.format(startDate, options.dayPopoverFormat);
      return y(DayCellContainer, { elRef: this.handleRootEl, date: startDate, dateProfile, todayRange }, (InnerContent, renderProps, elAttrs) => y(
        Popover,
        { elRef: elAttrs.ref, id: props.id, title, extraClassNames: ["fc-more-popover"].concat(elAttrs.className || []), extraAttrs: elAttrs, parentEl: props.parentEl, alignmentEl: props.alignmentEl, alignGridTop: props.alignGridTop, onClose: props.onClose },
        hasCustomDayCellContent(options) && y(InnerContent, { elTag: "div", elClasses: ["fc-more-popover-misc"] }),
        props.children
      ));
    }
    queryHit(positionLeft, positionTop, elWidth, elHeight) {
      let { rootEl, props } = this;
      if (positionLeft >= 0 && positionLeft < elWidth && positionTop >= 0 && positionTop < elHeight) {
        return {
          dateProfile: props.dateProfile,
          dateSpan: Object.assign({ allDay: !props.forceTimed, range: {
            start: props.startDate,
            end: props.endDate
          } }, props.extraDateSpan),
          dayEl: rootEl,
          rect: {
            left: 0,
            top: 0,
            right: elWidth,
            bottom: elHeight
          },
          layer: 1
        };
      }
      return null;
    }
  };
  var MoreLinkContainer = class extends BaseComponent {
    constructor() {
      super(...arguments);
      this.state = {
        isPopoverOpen: false,
        popoverId: getUniqueDomId()
      };
      this.handleLinkEl = (linkEl) => {
        this.linkEl = linkEl;
        if (this.props.elRef) {
          setRef(this.props.elRef, linkEl);
        }
      };
      this.handleClick = (ev) => {
        let { props, context } = this;
        let { moreLinkClick } = context.options;
        let date = computeRange(props).start;
        function buildPublicSeg(seg) {
          let { def, instance, range } = seg.eventRange;
          return {
            event: new EventImpl(context, def, instance),
            start: context.dateEnv.toDate(range.start),
            end: context.dateEnv.toDate(range.end),
            isStart: seg.isStart,
            isEnd: seg.isEnd
          };
        }
        if (typeof moreLinkClick === "function") {
          moreLinkClick = moreLinkClick({
            date,
            allDay: Boolean(props.allDayDate),
            allSegs: props.allSegs.map(buildPublicSeg),
            hiddenSegs: props.hiddenSegs.map(buildPublicSeg),
            jsEvent: ev,
            view: context.viewApi
          });
        }
        if (!moreLinkClick || moreLinkClick === "popover") {
          this.setState({ isPopoverOpen: true });
        } else if (typeof moreLinkClick === "string") {
          context.calendarApi.zoomTo(date, moreLinkClick);
        }
      };
      this.handlePopoverClose = () => {
        this.setState({ isPopoverOpen: false });
      };
    }
    render() {
      let { props, state } = this;
      return y(ViewContextType.Consumer, null, (context) => {
        let { viewApi, options, calendarApi } = context;
        let { moreLinkText } = options;
        let { moreCnt } = props;
        let range = computeRange(props);
        let text = typeof moreLinkText === "function" ? moreLinkText.call(calendarApi, moreCnt) : `+${moreCnt} ${moreLinkText}`;
        let hint = formatWithOrdinals(options.moreLinkHint, [moreCnt], text);
        let renderProps = {
          num: moreCnt,
          shortText: `+${moreCnt}`,
          text,
          view: viewApi
        };
        return y(
          _,
          null,
          Boolean(props.moreCnt) && y(ContentContainer, { elTag: props.elTag || "a", elRef: this.handleLinkEl, elClasses: [
            ...props.elClasses || [],
            "fc-more-link"
          ], elStyle: props.elStyle, elAttrs: Object.assign(Object.assign(Object.assign({}, props.elAttrs), createAriaClickAttrs(this.handleClick)), { title: hint, "aria-expanded": state.isPopoverOpen, "aria-controls": state.isPopoverOpen ? state.popoverId : "" }), renderProps, generatorName: "moreLinkContent", customGenerator: options.moreLinkContent, defaultGenerator: props.defaultGenerator || renderMoreLinkInner, classNameGenerator: options.moreLinkClassNames, didMount: options.moreLinkDidMount, willUnmount: options.moreLinkWillUnmount }, props.children),
          state.isPopoverOpen && y(MorePopover, { id: state.popoverId, startDate: range.start, endDate: range.end, dateProfile: props.dateProfile, todayRange: props.todayRange, extraDateSpan: props.extraDateSpan, parentEl: this.parentEl, alignmentEl: props.alignmentElRef ? props.alignmentElRef.current : this.linkEl, alignGridTop: props.alignGridTop, forceTimed: props.forceTimed, onClose: this.handlePopoverClose }, props.popoverContent())
        );
      });
    }
    componentDidMount() {
      this.updateParentEl();
    }
    componentDidUpdate() {
      this.updateParentEl();
    }
    updateParentEl() {
      if (this.linkEl) {
        this.parentEl = elementClosest(this.linkEl, ".fc-view-harness");
      }
    }
  };
  function renderMoreLinkInner(props) {
    return props.text;
  }
  function computeRange(props) {
    if (props.allDayDate) {
      return {
        start: props.allDayDate,
        end: addDays(props.allDayDate, 1)
      };
    }
    let { hiddenSegs } = props;
    return {
      start: computeEarliestSegStart(hiddenSegs),
      end: computeLatestSegEnd(hiddenSegs)
    };
  }
  function computeEarliestSegStart(segs) {
    return segs.reduce(pickEarliestStart).eventRange.range.start;
  }
  function pickEarliestStart(seg0, seg1) {
    return seg0.eventRange.range.start < seg1.eventRange.range.start ? seg0 : seg1;
  }
  function computeLatestSegEnd(segs) {
    return segs.reduce(pickLatestEnd).eventRange.range.end;
  }
  function pickLatestEnd(seg0, seg1) {
    return seg0.eventRange.range.end > seg1.eventRange.range.end ? seg0 : seg1;
  }

  // ../ifitwala_ed/node_modules/@fullcalendar/core/index.js
  var globalLocales = [];
  var MINIMAL_RAW_EN_LOCALE = {
    code: "en",
    week: {
      dow: 0,
      doy: 4
    },
    direction: "ltr",
    buttonText: {
      prev: "prev",
      next: "next",
      prevYear: "prev year",
      nextYear: "next year",
      year: "year",
      today: "today",
      month: "month",
      week: "week",
      day: "day",
      list: "list"
    },
    weekText: "W",
    weekTextLong: "Week",
    closeHint: "Close",
    timeHint: "Time",
    eventHint: "Event",
    allDayText: "all-day",
    moreLinkText: "more",
    noEventsText: "No events to display"
  };
  var RAW_EN_LOCALE = Object.assign(Object.assign({}, MINIMAL_RAW_EN_LOCALE), {
    buttonHints: {
      prev: "Previous $0",
      next: "Next $0",
      today(buttonText, unit) {
        return unit === "day" ? "Today" : `This ${buttonText}`;
      }
    },
    viewHint: "$0 view",
    navLinkHint: "Go to $0",
    moreLinkHint(eventCnt) {
      return `Show ${eventCnt} more event${eventCnt === 1 ? "" : "s"}`;
    }
  });
  function organizeRawLocales(explicitRawLocales) {
    let defaultCode = explicitRawLocales.length > 0 ? explicitRawLocales[0].code : "en";
    let allRawLocales = globalLocales.concat(explicitRawLocales);
    let rawLocaleMap = {
      en: RAW_EN_LOCALE
    };
    for (let rawLocale of allRawLocales) {
      rawLocaleMap[rawLocale.code] = rawLocale;
    }
    return {
      map: rawLocaleMap,
      defaultCode
    };
  }
  function buildLocale(inputSingular, available) {
    if (typeof inputSingular === "object" && !Array.isArray(inputSingular)) {
      return parseLocale(inputSingular.code, [inputSingular.code], inputSingular);
    }
    return queryLocale(inputSingular, available);
  }
  function queryLocale(codeArg, available) {
    let codes = [].concat(codeArg || []);
    let raw = queryRawLocale(codes, available) || RAW_EN_LOCALE;
    return parseLocale(codeArg, codes, raw);
  }
  function queryRawLocale(codes, available) {
    for (let i3 = 0; i3 < codes.length; i3 += 1) {
      let parts = codes[i3].toLocaleLowerCase().split("-");
      for (let j4 = parts.length; j4 > 0; j4 -= 1) {
        let simpleId = parts.slice(0, j4).join("-");
        if (available[simpleId]) {
          return available[simpleId];
        }
      }
    }
    return null;
  }
  function parseLocale(codeArg, codes, raw) {
    let merged = mergeProps([MINIMAL_RAW_EN_LOCALE, raw], ["buttonText"]);
    delete merged.code;
    let { week } = merged;
    delete merged.week;
    return {
      codeArg,
      codes,
      week,
      simpleNumberFormat: new Intl.NumberFormat(codeArg),
      options: merged
    };
  }
  function createPlugin(input) {
    return {
      id: guid(),
      name: input.name,
      premiumReleaseDate: input.premiumReleaseDate ? new Date(input.premiumReleaseDate) : void 0,
      deps: input.deps || [],
      reducers: input.reducers || [],
      isLoadingFuncs: input.isLoadingFuncs || [],
      contextInit: [].concat(input.contextInit || []),
      eventRefiners: input.eventRefiners || {},
      eventDefMemberAdders: input.eventDefMemberAdders || [],
      eventSourceRefiners: input.eventSourceRefiners || {},
      isDraggableTransformers: input.isDraggableTransformers || [],
      eventDragMutationMassagers: input.eventDragMutationMassagers || [],
      eventDefMutationAppliers: input.eventDefMutationAppliers || [],
      dateSelectionTransformers: input.dateSelectionTransformers || [],
      datePointTransforms: input.datePointTransforms || [],
      dateSpanTransforms: input.dateSpanTransforms || [],
      views: input.views || {},
      viewPropsTransformers: input.viewPropsTransformers || [],
      isPropsValid: input.isPropsValid || null,
      externalDefTransforms: input.externalDefTransforms || [],
      viewContainerAppends: input.viewContainerAppends || [],
      eventDropTransformers: input.eventDropTransformers || [],
      componentInteractions: input.componentInteractions || [],
      calendarInteractions: input.calendarInteractions || [],
      themeClasses: input.themeClasses || {},
      eventSourceDefs: input.eventSourceDefs || [],
      cmdFormatter: input.cmdFormatter,
      recurringTypes: input.recurringTypes || [],
      namedTimeZonedImpl: input.namedTimeZonedImpl,
      initialView: input.initialView || "",
      elementDraggingImpl: input.elementDraggingImpl,
      optionChangeHandlers: input.optionChangeHandlers || {},
      scrollGridImpl: input.scrollGridImpl || null,
      listenerRefiners: input.listenerRefiners || {},
      optionRefiners: input.optionRefiners || {},
      propSetHandlers: input.propSetHandlers || {}
    };
  }
  function buildPluginHooks(pluginDefs, globalDefs) {
    let currentPluginIds = {};
    let hooks = {
      premiumReleaseDate: void 0,
      reducers: [],
      isLoadingFuncs: [],
      contextInit: [],
      eventRefiners: {},
      eventDefMemberAdders: [],
      eventSourceRefiners: {},
      isDraggableTransformers: [],
      eventDragMutationMassagers: [],
      eventDefMutationAppliers: [],
      dateSelectionTransformers: [],
      datePointTransforms: [],
      dateSpanTransforms: [],
      views: {},
      viewPropsTransformers: [],
      isPropsValid: null,
      externalDefTransforms: [],
      viewContainerAppends: [],
      eventDropTransformers: [],
      componentInteractions: [],
      calendarInteractions: [],
      themeClasses: {},
      eventSourceDefs: [],
      cmdFormatter: null,
      recurringTypes: [],
      namedTimeZonedImpl: null,
      initialView: "",
      elementDraggingImpl: null,
      optionChangeHandlers: {},
      scrollGridImpl: null,
      listenerRefiners: {},
      optionRefiners: {},
      propSetHandlers: {}
    };
    function addDefs(defs) {
      for (let def of defs) {
        const pluginName = def.name;
        const currentId = currentPluginIds[pluginName];
        if (currentId === void 0) {
          currentPluginIds[pluginName] = def.id;
          addDefs(def.deps);
          hooks = combineHooks(hooks, def);
        } else if (currentId !== def.id) {
          console.warn(`Duplicate plugin '${pluginName}'`);
        }
      }
    }
    if (pluginDefs) {
      addDefs(pluginDefs);
    }
    addDefs(globalDefs);
    return hooks;
  }
  function buildBuildPluginHooks() {
    let currentOverrideDefs = [];
    let currentGlobalDefs = [];
    let currentHooks;
    return (overrideDefs, globalDefs) => {
      if (!currentHooks || !isArraysEqual(overrideDefs, currentOverrideDefs) || !isArraysEqual(globalDefs, currentGlobalDefs)) {
        currentHooks = buildPluginHooks(overrideDefs, globalDefs);
      }
      currentOverrideDefs = overrideDefs;
      currentGlobalDefs = globalDefs;
      return currentHooks;
    };
  }
  function combineHooks(hooks0, hooks1) {
    return {
      premiumReleaseDate: compareOptionalDates(hooks0.premiumReleaseDate, hooks1.premiumReleaseDate),
      reducers: hooks0.reducers.concat(hooks1.reducers),
      isLoadingFuncs: hooks0.isLoadingFuncs.concat(hooks1.isLoadingFuncs),
      contextInit: hooks0.contextInit.concat(hooks1.contextInit),
      eventRefiners: Object.assign(Object.assign({}, hooks0.eventRefiners), hooks1.eventRefiners),
      eventDefMemberAdders: hooks0.eventDefMemberAdders.concat(hooks1.eventDefMemberAdders),
      eventSourceRefiners: Object.assign(Object.assign({}, hooks0.eventSourceRefiners), hooks1.eventSourceRefiners),
      isDraggableTransformers: hooks0.isDraggableTransformers.concat(hooks1.isDraggableTransformers),
      eventDragMutationMassagers: hooks0.eventDragMutationMassagers.concat(hooks1.eventDragMutationMassagers),
      eventDefMutationAppliers: hooks0.eventDefMutationAppliers.concat(hooks1.eventDefMutationAppliers),
      dateSelectionTransformers: hooks0.dateSelectionTransformers.concat(hooks1.dateSelectionTransformers),
      datePointTransforms: hooks0.datePointTransforms.concat(hooks1.datePointTransforms),
      dateSpanTransforms: hooks0.dateSpanTransforms.concat(hooks1.dateSpanTransforms),
      views: Object.assign(Object.assign({}, hooks0.views), hooks1.views),
      viewPropsTransformers: hooks0.viewPropsTransformers.concat(hooks1.viewPropsTransformers),
      isPropsValid: hooks1.isPropsValid || hooks0.isPropsValid,
      externalDefTransforms: hooks0.externalDefTransforms.concat(hooks1.externalDefTransforms),
      viewContainerAppends: hooks0.viewContainerAppends.concat(hooks1.viewContainerAppends),
      eventDropTransformers: hooks0.eventDropTransformers.concat(hooks1.eventDropTransformers),
      calendarInteractions: hooks0.calendarInteractions.concat(hooks1.calendarInteractions),
      componentInteractions: hooks0.componentInteractions.concat(hooks1.componentInteractions),
      themeClasses: Object.assign(Object.assign({}, hooks0.themeClasses), hooks1.themeClasses),
      eventSourceDefs: hooks0.eventSourceDefs.concat(hooks1.eventSourceDefs),
      cmdFormatter: hooks1.cmdFormatter || hooks0.cmdFormatter,
      recurringTypes: hooks0.recurringTypes.concat(hooks1.recurringTypes),
      namedTimeZonedImpl: hooks1.namedTimeZonedImpl || hooks0.namedTimeZonedImpl,
      initialView: hooks0.initialView || hooks1.initialView,
      elementDraggingImpl: hooks0.elementDraggingImpl || hooks1.elementDraggingImpl,
      optionChangeHandlers: Object.assign(Object.assign({}, hooks0.optionChangeHandlers), hooks1.optionChangeHandlers),
      scrollGridImpl: hooks1.scrollGridImpl || hooks0.scrollGridImpl,
      listenerRefiners: Object.assign(Object.assign({}, hooks0.listenerRefiners), hooks1.listenerRefiners),
      optionRefiners: Object.assign(Object.assign({}, hooks0.optionRefiners), hooks1.optionRefiners),
      propSetHandlers: Object.assign(Object.assign({}, hooks0.propSetHandlers), hooks1.propSetHandlers)
    };
  }
  function compareOptionalDates(date0, date1) {
    if (date0 === void 0) {
      return date1;
    }
    if (date1 === void 0) {
      return date0;
    }
    return new Date(Math.max(date0.valueOf(), date1.valueOf()));
  }
  var StandardTheme = class extends Theme {
  };
  StandardTheme.prototype.classes = {
    root: "fc-theme-standard",
    tableCellShaded: "fc-cell-shaded",
    buttonGroup: "fc-button-group",
    button: "fc-button fc-button-primary",
    buttonActive: "fc-button-active"
  };
  StandardTheme.prototype.baseIconClass = "fc-icon";
  StandardTheme.prototype.iconClasses = {
    close: "fc-icon-x",
    prev: "fc-icon-chevron-left",
    next: "fc-icon-chevron-right",
    prevYear: "fc-icon-chevrons-left",
    nextYear: "fc-icon-chevrons-right"
  };
  StandardTheme.prototype.rtlIconClasses = {
    prev: "fc-icon-chevron-right",
    next: "fc-icon-chevron-left",
    prevYear: "fc-icon-chevrons-right",
    nextYear: "fc-icon-chevrons-left"
  };
  StandardTheme.prototype.iconOverrideOption = "buttonIcons";
  StandardTheme.prototype.iconOverrideCustomButtonOption = "icon";
  StandardTheme.prototype.iconOverridePrefix = "fc-icon-";
  function compileViewDefs(defaultConfigs, overrideConfigs) {
    let hash = {};
    let viewType;
    for (viewType in defaultConfigs) {
      ensureViewDef(viewType, hash, defaultConfigs, overrideConfigs);
    }
    for (viewType in overrideConfigs) {
      ensureViewDef(viewType, hash, defaultConfigs, overrideConfigs);
    }
    return hash;
  }
  function ensureViewDef(viewType, hash, defaultConfigs, overrideConfigs) {
    if (hash[viewType]) {
      return hash[viewType];
    }
    let viewDef = buildViewDef(viewType, hash, defaultConfigs, overrideConfigs);
    if (viewDef) {
      hash[viewType] = viewDef;
    }
    return viewDef;
  }
  function buildViewDef(viewType, hash, defaultConfigs, overrideConfigs) {
    let defaultConfig = defaultConfigs[viewType];
    let overrideConfig = overrideConfigs[viewType];
    let queryProp = (name) => defaultConfig && defaultConfig[name] !== null ? defaultConfig[name] : overrideConfig && overrideConfig[name] !== null ? overrideConfig[name] : null;
    let theComponent = queryProp("component");
    let superType = queryProp("superType");
    let superDef = null;
    if (superType) {
      if (superType === viewType) {
        throw new Error("Can't have a custom view type that references itself");
      }
      superDef = ensureViewDef(superType, hash, defaultConfigs, overrideConfigs);
    }
    if (!theComponent && superDef) {
      theComponent = superDef.component;
    }
    if (!theComponent) {
      return null;
    }
    return {
      type: viewType,
      component: theComponent,
      defaults: Object.assign(Object.assign({}, superDef ? superDef.defaults : {}), defaultConfig ? defaultConfig.rawOptions : {}),
      overrides: Object.assign(Object.assign({}, superDef ? superDef.overrides : {}), overrideConfig ? overrideConfig.rawOptions : {})
    };
  }
  function parseViewConfigs(inputs) {
    return mapHash(inputs, parseViewConfig);
  }
  function parseViewConfig(input) {
    let rawOptions = typeof input === "function" ? { component: input } : input;
    let { component } = rawOptions;
    if (rawOptions.content) {
      component = createViewHookComponent(rawOptions);
    } else if (component && !(component.prototype instanceof BaseComponent)) {
      component = createViewHookComponent(Object.assign(Object.assign({}, rawOptions), { content: component }));
    }
    return {
      superType: rawOptions.type,
      component,
      rawOptions
    };
  }
  function createViewHookComponent(options) {
    return (viewProps) => y(ViewContextType.Consumer, null, (context) => y(ContentContainer, { elTag: "div", elClasses: buildViewClassNames(context.viewSpec), renderProps: Object.assign(Object.assign({}, viewProps), { nextDayThreshold: context.options.nextDayThreshold }), generatorName: void 0, customGenerator: options.content, classNameGenerator: options.classNames, didMount: options.didMount, willUnmount: options.willUnmount }));
  }
  function buildViewSpecs(defaultInputs, optionOverrides, dynamicOptionOverrides, localeDefaults) {
    let defaultConfigs = parseViewConfigs(defaultInputs);
    let overrideConfigs = parseViewConfigs(optionOverrides.views);
    let viewDefs = compileViewDefs(defaultConfigs, overrideConfigs);
    return mapHash(viewDefs, (viewDef) => buildViewSpec(viewDef, overrideConfigs, optionOverrides, dynamicOptionOverrides, localeDefaults));
  }
  function buildViewSpec(viewDef, overrideConfigs, optionOverrides, dynamicOptionOverrides, localeDefaults) {
    let durationInput = viewDef.overrides.duration || viewDef.defaults.duration || dynamicOptionOverrides.duration || optionOverrides.duration;
    let duration = null;
    let durationUnit = "";
    let singleUnit = "";
    let singleUnitOverrides = {};
    if (durationInput) {
      duration = createDurationCached(durationInput);
      if (duration) {
        let denom = greatestDurationDenominator(duration);
        durationUnit = denom.unit;
        if (denom.value === 1) {
          singleUnit = durationUnit;
          singleUnitOverrides = overrideConfigs[durationUnit] ? overrideConfigs[durationUnit].rawOptions : {};
        }
      }
    }
    let queryButtonText = (optionsSubset) => {
      let buttonTextMap = optionsSubset.buttonText || {};
      let buttonTextKey = viewDef.defaults.buttonTextKey;
      if (buttonTextKey != null && buttonTextMap[buttonTextKey] != null) {
        return buttonTextMap[buttonTextKey];
      }
      if (buttonTextMap[viewDef.type] != null) {
        return buttonTextMap[viewDef.type];
      }
      if (buttonTextMap[singleUnit] != null) {
        return buttonTextMap[singleUnit];
      }
      return null;
    };
    let queryButtonTitle = (optionsSubset) => {
      let buttonHints = optionsSubset.buttonHints || {};
      let buttonKey = viewDef.defaults.buttonTextKey;
      if (buttonKey != null && buttonHints[buttonKey] != null) {
        return buttonHints[buttonKey];
      }
      if (buttonHints[viewDef.type] != null) {
        return buttonHints[viewDef.type];
      }
      if (buttonHints[singleUnit] != null) {
        return buttonHints[singleUnit];
      }
      return null;
    };
    return {
      type: viewDef.type,
      component: viewDef.component,
      duration,
      durationUnit,
      singleUnit,
      optionDefaults: viewDef.defaults,
      optionOverrides: Object.assign(Object.assign({}, singleUnitOverrides), viewDef.overrides),
      buttonTextOverride: queryButtonText(dynamicOptionOverrides) || queryButtonText(optionOverrides) || viewDef.overrides.buttonText,
      buttonTextDefault: queryButtonText(localeDefaults) || viewDef.defaults.buttonText || queryButtonText(BASE_OPTION_DEFAULTS) || viewDef.type,
      buttonTitleOverride: queryButtonTitle(dynamicOptionOverrides) || queryButtonTitle(optionOverrides) || viewDef.overrides.buttonHint,
      buttonTitleDefault: queryButtonTitle(localeDefaults) || viewDef.defaults.buttonHint || queryButtonTitle(BASE_OPTION_DEFAULTS)
    };
  }
  var durationInputMap = {};
  function createDurationCached(durationInput) {
    let json = JSON.stringify(durationInput);
    let res = durationInputMap[json];
    if (res === void 0) {
      res = createDuration(durationInput);
      durationInputMap[json] = res;
    }
    return res;
  }
  function reduceViewType(viewType, action) {
    switch (action.type) {
      case "CHANGE_VIEW_TYPE":
        viewType = action.viewType;
    }
    return viewType;
  }
  function reduceCurrentDate(currentDate, action) {
    switch (action.type) {
      case "CHANGE_DATE":
        return action.dateMarker;
      default:
        return currentDate;
    }
  }
  function getInitialDate(options, dateEnv, nowManager) {
    let initialDateInput = options.initialDate;
    if (initialDateInput != null) {
      return dateEnv.createMarker(initialDateInput);
    }
    return nowManager.getDateMarker();
  }
  function reduceDynamicOptionOverrides(dynamicOptionOverrides, action) {
    switch (action.type) {
      case "SET_OPTION":
        return Object.assign(Object.assign({}, dynamicOptionOverrides), { [action.optionName]: action.rawOptionValue });
      default:
        return dynamicOptionOverrides;
    }
  }
  function reduceDateProfile(currentDateProfile, action, currentDate, dateProfileGenerator) {
    let dp;
    switch (action.type) {
      case "CHANGE_VIEW_TYPE":
        return dateProfileGenerator.build(action.dateMarker || currentDate);
      case "CHANGE_DATE":
        return dateProfileGenerator.build(action.dateMarker);
      case "PREV":
        dp = dateProfileGenerator.buildPrev(currentDateProfile, currentDate);
        if (dp.isValid) {
          return dp;
        }
        break;
      case "NEXT":
        dp = dateProfileGenerator.buildNext(currentDateProfile, currentDate);
        if (dp.isValid) {
          return dp;
        }
        break;
    }
    return currentDateProfile;
  }
  function initEventSources(calendarOptions, dateProfile, context) {
    let activeRange = dateProfile ? dateProfile.activeRange : null;
    return addSources({}, parseInitialSources(calendarOptions, context), activeRange, context);
  }
  function reduceEventSources(eventSources, action, dateProfile, context) {
    let activeRange = dateProfile ? dateProfile.activeRange : null;
    switch (action.type) {
      case "ADD_EVENT_SOURCES":
        return addSources(eventSources, action.sources, activeRange, context);
      case "REMOVE_EVENT_SOURCE":
        return removeSource(eventSources, action.sourceId);
      case "PREV":
      case "NEXT":
      case "CHANGE_DATE":
      case "CHANGE_VIEW_TYPE":
        if (dateProfile) {
          return fetchDirtySources(eventSources, activeRange, context);
        }
        return eventSources;
      case "FETCH_EVENT_SOURCES":
        return fetchSourcesByIds(eventSources, action.sourceIds ? arrayToHash(action.sourceIds) : excludeStaticSources(eventSources, context), activeRange, action.isRefetch || false, context);
      case "RECEIVE_EVENTS":
      case "RECEIVE_EVENT_ERROR":
        return receiveResponse(eventSources, action.sourceId, action.fetchId, action.fetchRange);
      case "REMOVE_ALL_EVENT_SOURCES":
        return {};
      default:
        return eventSources;
    }
  }
  function reduceEventSourcesNewTimeZone(eventSources, dateProfile, context) {
    let activeRange = dateProfile ? dateProfile.activeRange : null;
    return fetchSourcesByIds(eventSources, excludeStaticSources(eventSources, context), activeRange, true, context);
  }
  function computeEventSourcesLoading(eventSources) {
    for (let sourceId in eventSources) {
      if (eventSources[sourceId].isFetching) {
        return true;
      }
    }
    return false;
  }
  function addSources(eventSourceHash, sources, fetchRange, context) {
    let hash = {};
    for (let source of sources) {
      hash[source.sourceId] = source;
    }
    if (fetchRange) {
      hash = fetchDirtySources(hash, fetchRange, context);
    }
    return Object.assign(Object.assign({}, eventSourceHash), hash);
  }
  function removeSource(eventSourceHash, sourceId) {
    return filterHash(eventSourceHash, (eventSource) => eventSource.sourceId !== sourceId);
  }
  function fetchDirtySources(sourceHash, fetchRange, context) {
    return fetchSourcesByIds(sourceHash, filterHash(sourceHash, (eventSource) => isSourceDirty(eventSource, fetchRange, context)), fetchRange, false, context);
  }
  function isSourceDirty(eventSource, fetchRange, context) {
    if (!doesSourceNeedRange(eventSource, context)) {
      return !eventSource.latestFetchId;
    }
    return !context.options.lazyFetching || !eventSource.fetchRange || eventSource.isFetching || fetchRange.start < eventSource.fetchRange.start || fetchRange.end > eventSource.fetchRange.end;
  }
  function fetchSourcesByIds(prevSources, sourceIdHash, fetchRange, isRefetch, context) {
    let nextSources = {};
    for (let sourceId in prevSources) {
      let source = prevSources[sourceId];
      if (sourceIdHash[sourceId]) {
        nextSources[sourceId] = fetchSource(source, fetchRange, isRefetch, context);
      } else {
        nextSources[sourceId] = source;
      }
    }
    return nextSources;
  }
  function fetchSource(eventSource, fetchRange, isRefetch, context) {
    let { options, calendarApi } = context;
    let sourceDef = context.pluginHooks.eventSourceDefs[eventSource.sourceDefId];
    let fetchId = guid();
    sourceDef.fetch({
      eventSource,
      range: fetchRange,
      isRefetch,
      context
    }, (res) => {
      let { rawEvents } = res;
      if (options.eventSourceSuccess) {
        rawEvents = options.eventSourceSuccess.call(calendarApi, rawEvents, res.response) || rawEvents;
      }
      if (eventSource.success) {
        rawEvents = eventSource.success.call(calendarApi, rawEvents, res.response) || rawEvents;
      }
      context.dispatch({
        type: "RECEIVE_EVENTS",
        sourceId: eventSource.sourceId,
        fetchId,
        fetchRange,
        rawEvents
      });
    }, (error) => {
      let errorHandled = false;
      if (options.eventSourceFailure) {
        options.eventSourceFailure.call(calendarApi, error);
        errorHandled = true;
      }
      if (eventSource.failure) {
        eventSource.failure(error);
        errorHandled = true;
      }
      if (!errorHandled) {
        console.warn(error.message, error);
      }
      context.dispatch({
        type: "RECEIVE_EVENT_ERROR",
        sourceId: eventSource.sourceId,
        fetchId,
        fetchRange,
        error
      });
    });
    return Object.assign(Object.assign({}, eventSource), { isFetching: true, latestFetchId: fetchId });
  }
  function receiveResponse(sourceHash, sourceId, fetchId, fetchRange) {
    let eventSource = sourceHash[sourceId];
    if (eventSource && fetchId === eventSource.latestFetchId) {
      return Object.assign(Object.assign({}, sourceHash), { [sourceId]: Object.assign(Object.assign({}, eventSource), { isFetching: false, fetchRange }) });
    }
    return sourceHash;
  }
  function excludeStaticSources(eventSources, context) {
    return filterHash(eventSources, (eventSource) => doesSourceNeedRange(eventSource, context));
  }
  function parseInitialSources(rawOptions, context) {
    let refiners = buildEventSourceRefiners(context);
    let rawSources = [].concat(rawOptions.eventSources || []);
    let sources = [];
    if (rawOptions.initialEvents) {
      rawSources.unshift(rawOptions.initialEvents);
    }
    if (rawOptions.events) {
      rawSources.unshift(rawOptions.events);
    }
    for (let rawSource of rawSources) {
      let source = parseEventSource(rawSource, context, refiners);
      if (source) {
        sources.push(source);
      }
    }
    return sources;
  }
  function doesSourceNeedRange(eventSource, context) {
    let defs = context.pluginHooks.eventSourceDefs;
    return !defs[eventSource.sourceDefId].ignoreRange;
  }
  function reduceDateSelection(currentSelection, action) {
    switch (action.type) {
      case "UNSELECT_DATES":
        return null;
      case "SELECT_DATES":
        return action.selection;
      default:
        return currentSelection;
    }
  }
  function reduceSelectedEvent(currentInstanceId, action) {
    switch (action.type) {
      case "UNSELECT_EVENT":
        return "";
      case "SELECT_EVENT":
        return action.eventInstanceId;
      default:
        return currentInstanceId;
    }
  }
  function reduceEventDrag(currentDrag, action) {
    let newDrag;
    switch (action.type) {
      case "UNSET_EVENT_DRAG":
        return null;
      case "SET_EVENT_DRAG":
        newDrag = action.state;
        return {
          affectedEvents: newDrag.affectedEvents,
          mutatedEvents: newDrag.mutatedEvents,
          isEvent: newDrag.isEvent
        };
      default:
        return currentDrag;
    }
  }
  function reduceEventResize(currentResize, action) {
    let newResize;
    switch (action.type) {
      case "UNSET_EVENT_RESIZE":
        return null;
      case "SET_EVENT_RESIZE":
        newResize = action.state;
        return {
          affectedEvents: newResize.affectedEvents,
          mutatedEvents: newResize.mutatedEvents,
          isEvent: newResize.isEvent
        };
      default:
        return currentResize;
    }
  }
  function parseToolbars(calendarOptions, calendarOptionOverrides, theme, viewSpecs, calendarApi) {
    let header = calendarOptions.headerToolbar ? parseToolbar(calendarOptions.headerToolbar, calendarOptions, calendarOptionOverrides, theme, viewSpecs, calendarApi) : null;
    let footer = calendarOptions.footerToolbar ? parseToolbar(calendarOptions.footerToolbar, calendarOptions, calendarOptionOverrides, theme, viewSpecs, calendarApi) : null;
    return { header, footer };
  }
  function parseToolbar(sectionStrHash, calendarOptions, calendarOptionOverrides, theme, viewSpecs, calendarApi) {
    let sectionWidgets = {};
    let viewsWithButtons = [];
    let hasTitle = false;
    for (let sectionName in sectionStrHash) {
      let sectionStr = sectionStrHash[sectionName];
      let sectionRes = parseSection(sectionStr, calendarOptions, calendarOptionOverrides, theme, viewSpecs, calendarApi);
      sectionWidgets[sectionName] = sectionRes.widgets;
      viewsWithButtons.push(...sectionRes.viewsWithButtons);
      hasTitle = hasTitle || sectionRes.hasTitle;
    }
    return { sectionWidgets, viewsWithButtons, hasTitle };
  }
  function parseSection(sectionStr, calendarOptions, calendarOptionOverrides, theme, viewSpecs, calendarApi) {
    let isRtl = calendarOptions.direction === "rtl";
    let calendarCustomButtons = calendarOptions.customButtons || {};
    let calendarButtonTextOverrides = calendarOptionOverrides.buttonText || {};
    let calendarButtonText = calendarOptions.buttonText || {};
    let calendarButtonHintOverrides = calendarOptionOverrides.buttonHints || {};
    let calendarButtonHints = calendarOptions.buttonHints || {};
    let sectionSubstrs = sectionStr ? sectionStr.split(" ") : [];
    let viewsWithButtons = [];
    let hasTitle = false;
    let widgets = sectionSubstrs.map((buttonGroupStr) => buttonGroupStr.split(",").map((buttonName) => {
      if (buttonName === "title") {
        hasTitle = true;
        return { buttonName };
      }
      let customButtonProps;
      let viewSpec;
      let buttonClick;
      let buttonIcon;
      let buttonText;
      let buttonHint;
      if (customButtonProps = calendarCustomButtons[buttonName]) {
        buttonClick = (ev) => {
          if (customButtonProps.click) {
            customButtonProps.click.call(ev.target, ev, ev.target);
          }
        };
        (buttonIcon = theme.getCustomButtonIconClass(customButtonProps)) || (buttonIcon = theme.getIconClass(buttonName, isRtl)) || (buttonText = customButtonProps.text);
        buttonHint = customButtonProps.hint || customButtonProps.text;
      } else if (viewSpec = viewSpecs[buttonName]) {
        viewsWithButtons.push(buttonName);
        buttonClick = () => {
          calendarApi.changeView(buttonName);
        };
        (buttonText = viewSpec.buttonTextOverride) || (buttonIcon = theme.getIconClass(buttonName, isRtl)) || (buttonText = viewSpec.buttonTextDefault);
        let textFallback = viewSpec.buttonTextOverride || viewSpec.buttonTextDefault;
        buttonHint = formatWithOrdinals(
          viewSpec.buttonTitleOverride || viewSpec.buttonTitleDefault || calendarOptions.viewHint,
          [textFallback, buttonName],
          textFallback
        );
      } else if (calendarApi[buttonName]) {
        buttonClick = () => {
          calendarApi[buttonName]();
        };
        (buttonText = calendarButtonTextOverrides[buttonName]) || (buttonIcon = theme.getIconClass(buttonName, isRtl)) || (buttonText = calendarButtonText[buttonName]);
        if (buttonName === "prevYear" || buttonName === "nextYear") {
          let prevOrNext = buttonName === "prevYear" ? "prev" : "next";
          buttonHint = formatWithOrdinals(calendarButtonHintOverrides[prevOrNext] || calendarButtonHints[prevOrNext], [
            calendarButtonText.year || "year",
            "year"
          ], calendarButtonText[buttonName]);
        } else {
          buttonHint = (navUnit) => formatWithOrdinals(calendarButtonHintOverrides[buttonName] || calendarButtonHints[buttonName], [
            calendarButtonText[navUnit] || navUnit,
            navUnit
          ], calendarButtonText[buttonName]);
        }
      }
      return { buttonName, buttonClick, buttonIcon, buttonText, buttonHint };
    }));
    return { widgets, viewsWithButtons, hasTitle };
  }
  var ViewImpl = class {
    constructor(type, getCurrentData, dateEnv) {
      this.type = type;
      this.getCurrentData = getCurrentData;
      this.dateEnv = dateEnv;
    }
    get calendar() {
      return this.getCurrentData().calendarApi;
    }
    get title() {
      return this.getCurrentData().viewTitle;
    }
    get activeStart() {
      return this.dateEnv.toDate(this.getCurrentData().dateProfile.activeRange.start);
    }
    get activeEnd() {
      return this.dateEnv.toDate(this.getCurrentData().dateProfile.activeRange.end);
    }
    get currentStart() {
      return this.dateEnv.toDate(this.getCurrentData().dateProfile.currentRange.start);
    }
    get currentEnd() {
      return this.dateEnv.toDate(this.getCurrentData().dateProfile.currentRange.end);
    }
    getOption(name) {
      return this.getCurrentData().options[name];
    }
  };
  var eventSourceDef$2 = {
    ignoreRange: true,
    parseMeta(refined) {
      if (Array.isArray(refined.events)) {
        return refined.events;
      }
      return null;
    },
    fetch(arg, successCallback) {
      successCallback({
        rawEvents: arg.eventSource.meta
      });
    }
  };
  var arrayEventSourcePlugin = createPlugin({
    name: "array-event-source",
    eventSourceDefs: [eventSourceDef$2]
  });
  var eventSourceDef$1 = {
    parseMeta(refined) {
      if (typeof refined.events === "function") {
        return refined.events;
      }
      return null;
    },
    fetch(arg, successCallback, errorCallback) {
      const { dateEnv } = arg.context;
      const func = arg.eventSource.meta;
      unpromisify(func.bind(null, buildRangeApiWithTimeZone(arg.range, dateEnv)), (rawEvents) => successCallback({ rawEvents }), errorCallback);
    }
  };
  var funcEventSourcePlugin = createPlugin({
    name: "func-event-source",
    eventSourceDefs: [eventSourceDef$1]
  });
  var JSON_FEED_EVENT_SOURCE_REFINERS = {
    method: String,
    extraParams: identity,
    startParam: String,
    endParam: String,
    timeZoneParam: String
  };
  var eventSourceDef = {
    parseMeta(refined) {
      if (refined.url && (refined.format === "json" || !refined.format)) {
        return {
          url: refined.url,
          format: "json",
          method: (refined.method || "GET").toUpperCase(),
          extraParams: refined.extraParams,
          startParam: refined.startParam,
          endParam: refined.endParam,
          timeZoneParam: refined.timeZoneParam
        };
      }
      return null;
    },
    fetch(arg, successCallback, errorCallback) {
      const { meta } = arg.eventSource;
      const requestParams = buildRequestParams(meta, arg.range, arg.context);
      requestJson(meta.method, meta.url, requestParams).then(([rawEvents, response]) => {
        successCallback({ rawEvents, response });
      }, errorCallback);
    }
  };
  var jsonFeedEventSourcePlugin = createPlugin({
    name: "json-event-source",
    eventSourceRefiners: JSON_FEED_EVENT_SOURCE_REFINERS,
    eventSourceDefs: [eventSourceDef]
  });
  function buildRequestParams(meta, range, context) {
    let { dateEnv, options } = context;
    let startParam;
    let endParam;
    let timeZoneParam;
    let customRequestParams;
    let params = {};
    startParam = meta.startParam;
    if (startParam == null) {
      startParam = options.startParam;
    }
    endParam = meta.endParam;
    if (endParam == null) {
      endParam = options.endParam;
    }
    timeZoneParam = meta.timeZoneParam;
    if (timeZoneParam == null) {
      timeZoneParam = options.timeZoneParam;
    }
    if (typeof meta.extraParams === "function") {
      customRequestParams = meta.extraParams();
    } else {
      customRequestParams = meta.extraParams || {};
    }
    Object.assign(params, customRequestParams);
    params[startParam] = dateEnv.formatIso(range.start);
    params[endParam] = dateEnv.formatIso(range.end);
    if (dateEnv.timeZone !== "local") {
      params[timeZoneParam] = dateEnv.timeZone;
    }
    return params;
  }
  var SIMPLE_RECURRING_REFINERS = {
    daysOfWeek: identity,
    startTime: createDuration,
    endTime: createDuration,
    duration: createDuration,
    startRecur: identity,
    endRecur: identity
  };
  var recurring = {
    parse(refined, dateEnv) {
      if (refined.daysOfWeek || refined.startTime || refined.endTime || refined.startRecur || refined.endRecur) {
        let recurringData = {
          daysOfWeek: refined.daysOfWeek || null,
          startTime: refined.startTime || null,
          endTime: refined.endTime || null,
          startRecur: refined.startRecur ? dateEnv.createMarker(refined.startRecur) : null,
          endRecur: refined.endRecur ? dateEnv.createMarker(refined.endRecur) : null,
          dateEnv
        };
        let duration;
        if (refined.duration) {
          duration = refined.duration;
        }
        if (!duration && refined.startTime && refined.endTime) {
          duration = subtractDurations(refined.endTime, refined.startTime);
        }
        return {
          allDayGuess: Boolean(!refined.startTime && !refined.endTime),
          duration,
          typeData: recurringData
        };
      }
      return null;
    },
    expand(typeData, framingRange, dateEnv) {
      let clippedFramingRange = intersectRanges(framingRange, { start: typeData.startRecur, end: typeData.endRecur });
      if (clippedFramingRange) {
        return expandRanges(typeData.daysOfWeek, typeData.startTime, typeData.dateEnv, dateEnv, clippedFramingRange);
      }
      return [];
    }
  };
  var simpleRecurringEventsPlugin = createPlugin({
    name: "simple-recurring-event",
    recurringTypes: [recurring],
    eventRefiners: SIMPLE_RECURRING_REFINERS
  });
  function expandRanges(daysOfWeek, startTime, eventDateEnv, calendarDateEnv, framingRange) {
    let dowHash = daysOfWeek ? arrayToHash(daysOfWeek) : null;
    let dayMarker = startOfDay(framingRange.start);
    let endMarker = framingRange.end;
    let instanceStarts = [];
    while (dayMarker < endMarker) {
      let instanceStart;
      if (!dowHash || dowHash[dayMarker.getUTCDay()]) {
        if (startTime) {
          instanceStart = calendarDateEnv.add(dayMarker, startTime);
        } else {
          instanceStart = dayMarker;
        }
        instanceStarts.push(calendarDateEnv.createMarker(eventDateEnv.toDate(instanceStart)));
      }
      dayMarker = addDays(dayMarker, 1);
    }
    return instanceStarts;
  }
  var changeHandlerPlugin = createPlugin({
    name: "change-handler",
    optionChangeHandlers: {
      events(events, context) {
        handleEventSources([events], context);
      },
      eventSources: handleEventSources
    }
  });
  function handleEventSources(inputs, context) {
    let unfoundSources = hashValuesToArray(context.getCurrentData().eventSources);
    if (unfoundSources.length === 1 && inputs.length === 1 && Array.isArray(unfoundSources[0]._raw) && Array.isArray(inputs[0])) {
      context.dispatch({
        type: "RESET_RAW_EVENTS",
        sourceId: unfoundSources[0].sourceId,
        rawEvents: inputs[0]
      });
      return;
    }
    let newInputs = [];
    for (let input of inputs) {
      let inputFound = false;
      for (let i3 = 0; i3 < unfoundSources.length; i3 += 1) {
        if (unfoundSources[i3]._raw === input) {
          unfoundSources.splice(i3, 1);
          inputFound = true;
          break;
        }
      }
      if (!inputFound) {
        newInputs.push(input);
      }
    }
    for (let unfoundSource of unfoundSources) {
      context.dispatch({
        type: "REMOVE_EVENT_SOURCE",
        sourceId: unfoundSource.sourceId
      });
    }
    for (let newInput of newInputs) {
      context.calendarApi.addEventSource(newInput);
    }
  }
  function handleDateProfile(dateProfile, context) {
    context.emitter.trigger("datesSet", Object.assign(Object.assign({}, buildRangeApiWithTimeZone(dateProfile.activeRange, context.dateEnv)), { view: context.viewApi }));
  }
  function handleEventStore(eventStore, context) {
    let { emitter } = context;
    if (emitter.hasHandlers("eventsSet")) {
      emitter.trigger("eventsSet", buildEventApis(eventStore, context));
    }
  }
  var globalPlugins = [
    arrayEventSourcePlugin,
    funcEventSourcePlugin,
    jsonFeedEventSourcePlugin,
    simpleRecurringEventsPlugin,
    changeHandlerPlugin,
    createPlugin({
      name: "misc",
      isLoadingFuncs: [
        (state) => computeEventSourcesLoading(state.eventSources)
      ],
      propSetHandlers: {
        dateProfile: handleDateProfile,
        eventStore: handleEventStore
      }
    })
  ];
  var TaskRunner = class {
    constructor(runTaskOption, drainedOption) {
      this.runTaskOption = runTaskOption;
      this.drainedOption = drainedOption;
      this.queue = [];
      this.delayedRunner = new DelayedRunner(this.drain.bind(this));
    }
    request(task, delay) {
      this.queue.push(task);
      this.delayedRunner.request(delay);
    }
    pause(scope) {
      this.delayedRunner.pause(scope);
    }
    resume(scope, force) {
      this.delayedRunner.resume(scope, force);
    }
    drain() {
      let { queue } = this;
      while (queue.length) {
        let completedTasks = [];
        let task;
        while (task = queue.shift()) {
          this.runTask(task);
          completedTasks.push(task);
        }
        this.drained(completedTasks);
      }
    }
    runTask(task) {
      if (this.runTaskOption) {
        this.runTaskOption(task);
      }
    }
    drained(completedTasks) {
      if (this.drainedOption) {
        this.drainedOption(completedTasks);
      }
    }
  };
  function buildTitle(dateProfile, viewOptions, dateEnv) {
    let range;
    if (/^(year|month)$/.test(dateProfile.currentRangeUnit)) {
      range = dateProfile.currentRange;
    } else {
      range = dateProfile.activeRange;
    }
    return dateEnv.formatRange(range.start, range.end, createFormatter(viewOptions.titleFormat || buildTitleFormat(dateProfile)), {
      isEndExclusive: dateProfile.isRangeAllDay,
      defaultSeparator: viewOptions.titleRangeSeparator
    });
  }
  function buildTitleFormat(dateProfile) {
    let { currentRangeUnit } = dateProfile;
    if (currentRangeUnit === "year") {
      return { year: "numeric" };
    }
    if (currentRangeUnit === "month") {
      return { year: "numeric", month: "long" };
    }
    let days = diffWholeDays(dateProfile.currentRange.start, dateProfile.currentRange.end);
    if (days !== null && days > 1) {
      return { year: "numeric", month: "short", day: "numeric" };
    }
    return { year: "numeric", month: "long", day: "numeric" };
  }
  var CalendarNowManager = class {
    constructor() {
      this.resetListeners = /* @__PURE__ */ new Set();
    }
    handleInput(dateEnv, nowInput) {
      const oldDateEnv = this.dateEnv;
      if (dateEnv !== oldDateEnv) {
        if (typeof nowInput === "function") {
          this.nowFn = nowInput;
        } else if (!oldDateEnv) {
          this.nowAnchorDate = dateEnv.toDate(nowInput ? dateEnv.createMarker(nowInput) : dateEnv.createNowMarker());
          this.nowAnchorQueried = Date.now();
        }
        this.dateEnv = dateEnv;
        if (oldDateEnv) {
          for (const resetListener of this.resetListeners.values()) {
            resetListener();
          }
        }
      }
    }
    getDateMarker() {
      return this.nowAnchorDate ? this.dateEnv.timestampToMarker(this.nowAnchorDate.valueOf() + (Date.now() - this.nowAnchorQueried)) : this.dateEnv.createMarker(this.nowFn());
    }
    addResetListener(handler) {
      this.resetListeners.add(handler);
    }
    removeResetListener(handler) {
      this.resetListeners.delete(handler);
    }
  };
  var CalendarDataManager = class {
    constructor(props) {
      this.computeCurrentViewData = memoize(this._computeCurrentViewData);
      this.organizeRawLocales = memoize(organizeRawLocales);
      this.buildLocale = memoize(buildLocale);
      this.buildPluginHooks = buildBuildPluginHooks();
      this.buildDateEnv = memoize(buildDateEnv$1);
      this.buildTheme = memoize(buildTheme);
      this.parseToolbars = memoize(parseToolbars);
      this.buildViewSpecs = memoize(buildViewSpecs);
      this.buildDateProfileGenerator = memoizeObjArg(buildDateProfileGenerator);
      this.buildViewApi = memoize(buildViewApi);
      this.buildViewUiProps = memoizeObjArg(buildViewUiProps);
      this.buildEventUiBySource = memoize(buildEventUiBySource, isPropsEqual);
      this.buildEventUiBases = memoize(buildEventUiBases);
      this.parseContextBusinessHours = memoizeObjArg(parseContextBusinessHours);
      this.buildTitle = memoize(buildTitle);
      this.nowManager = new CalendarNowManager();
      this.emitter = new Emitter();
      this.actionRunner = new TaskRunner(this._handleAction.bind(this), this.updateData.bind(this));
      this.currentCalendarOptionsInput = {};
      this.currentCalendarOptionsRefined = {};
      this.currentViewOptionsInput = {};
      this.currentViewOptionsRefined = {};
      this.currentCalendarOptionsRefiners = {};
      this.optionsForRefining = [];
      this.optionsForHandling = [];
      this.getCurrentData = () => this.data;
      this.dispatch = (action) => {
        this.actionRunner.request(action);
      };
      this.props = props;
      this.actionRunner.pause();
      this.nowManager = new CalendarNowManager();
      let dynamicOptionOverrides = {};
      let optionsData = this.computeOptionsData(props.optionOverrides, dynamicOptionOverrides, props.calendarApi);
      let currentViewType = optionsData.calendarOptions.initialView || optionsData.pluginHooks.initialView;
      let currentViewData = this.computeCurrentViewData(currentViewType, optionsData, props.optionOverrides, dynamicOptionOverrides);
      props.calendarApi.currentDataManager = this;
      this.emitter.setThisContext(props.calendarApi);
      this.emitter.setOptions(currentViewData.options);
      let calendarContext = {
        nowManager: this.nowManager,
        dateEnv: optionsData.dateEnv,
        options: optionsData.calendarOptions,
        pluginHooks: optionsData.pluginHooks,
        calendarApi: props.calendarApi,
        dispatch: this.dispatch,
        emitter: this.emitter,
        getCurrentData: this.getCurrentData
      };
      let currentDate = getInitialDate(optionsData.calendarOptions, optionsData.dateEnv, this.nowManager);
      let dateProfile = currentViewData.dateProfileGenerator.build(currentDate);
      if (!rangeContainsMarker(dateProfile.activeRange, currentDate)) {
        currentDate = dateProfile.currentRange.start;
      }
      for (let callback of optionsData.pluginHooks.contextInit) {
        callback(calendarContext);
      }
      let eventSources = initEventSources(optionsData.calendarOptions, dateProfile, calendarContext);
      let initialState = {
        dynamicOptionOverrides,
        currentViewType,
        currentDate,
        dateProfile,
        businessHours: this.parseContextBusinessHours(calendarContext),
        eventSources,
        eventUiBases: {},
        eventStore: createEmptyEventStore(),
        renderableEventStore: createEmptyEventStore(),
        dateSelection: null,
        eventSelection: "",
        eventDrag: null,
        eventResize: null,
        selectionConfig: this.buildViewUiProps(calendarContext).selectionConfig
      };
      let contextAndState = Object.assign(Object.assign({}, calendarContext), initialState);
      for (let reducer of optionsData.pluginHooks.reducers) {
        Object.assign(initialState, reducer(null, null, contextAndState));
      }
      if (computeIsLoading(initialState, calendarContext)) {
        this.emitter.trigger("loading", true);
      }
      this.state = initialState;
      this.updateData();
      this.actionRunner.resume();
    }
    resetOptions(optionOverrides, changedOptionNames) {
      let { props } = this;
      if (changedOptionNames === void 0) {
        props.optionOverrides = optionOverrides;
      } else {
        props.optionOverrides = Object.assign(Object.assign({}, props.optionOverrides || {}), optionOverrides);
        this.optionsForRefining.push(...changedOptionNames);
      }
      if (changedOptionNames === void 0 || changedOptionNames.length) {
        this.actionRunner.request({
          type: "NOTHING"
        });
      }
    }
    _handleAction(action) {
      let { props, state, emitter } = this;
      let dynamicOptionOverrides = reduceDynamicOptionOverrides(state.dynamicOptionOverrides, action);
      let optionsData = this.computeOptionsData(props.optionOverrides, dynamicOptionOverrides, props.calendarApi);
      let currentViewType = reduceViewType(state.currentViewType, action);
      let currentViewData = this.computeCurrentViewData(currentViewType, optionsData, props.optionOverrides, dynamicOptionOverrides);
      props.calendarApi.currentDataManager = this;
      emitter.setThisContext(props.calendarApi);
      emitter.setOptions(currentViewData.options);
      let calendarContext = {
        nowManager: this.nowManager,
        dateEnv: optionsData.dateEnv,
        options: optionsData.calendarOptions,
        pluginHooks: optionsData.pluginHooks,
        calendarApi: props.calendarApi,
        dispatch: this.dispatch,
        emitter,
        getCurrentData: this.getCurrentData
      };
      let { currentDate, dateProfile } = state;
      if (this.data && this.data.dateProfileGenerator !== currentViewData.dateProfileGenerator) {
        dateProfile = currentViewData.dateProfileGenerator.build(currentDate);
      }
      currentDate = reduceCurrentDate(currentDate, action);
      dateProfile = reduceDateProfile(dateProfile, action, currentDate, currentViewData.dateProfileGenerator);
      if (action.type === "PREV" || action.type === "NEXT" || !rangeContainsMarker(dateProfile.currentRange, currentDate)) {
        currentDate = dateProfile.currentRange.start;
      }
      let eventSources = reduceEventSources(state.eventSources, action, dateProfile, calendarContext);
      let eventStore = reduceEventStore(state.eventStore, action, eventSources, dateProfile, calendarContext);
      let isEventsLoading = computeEventSourcesLoading(eventSources);
      let renderableEventStore = isEventsLoading && !currentViewData.options.progressiveEventRendering ? state.renderableEventStore || eventStore : eventStore;
      let { eventUiSingleBase, selectionConfig } = this.buildViewUiProps(calendarContext);
      let eventUiBySource = this.buildEventUiBySource(eventSources);
      let eventUiBases = this.buildEventUiBases(renderableEventStore.defs, eventUiSingleBase, eventUiBySource);
      let newState = {
        dynamicOptionOverrides,
        currentViewType,
        currentDate,
        dateProfile,
        eventSources,
        eventStore,
        renderableEventStore,
        selectionConfig,
        eventUiBases,
        businessHours: this.parseContextBusinessHours(calendarContext),
        dateSelection: reduceDateSelection(state.dateSelection, action),
        eventSelection: reduceSelectedEvent(state.eventSelection, action),
        eventDrag: reduceEventDrag(state.eventDrag, action),
        eventResize: reduceEventResize(state.eventResize, action)
      };
      let contextAndState = Object.assign(Object.assign({}, calendarContext), newState);
      for (let reducer of optionsData.pluginHooks.reducers) {
        Object.assign(newState, reducer(state, action, contextAndState));
      }
      let wasLoading = computeIsLoading(state, calendarContext);
      let isLoading = computeIsLoading(newState, calendarContext);
      if (!wasLoading && isLoading) {
        emitter.trigger("loading", true);
      } else if (wasLoading && !isLoading) {
        emitter.trigger("loading", false);
      }
      this.state = newState;
      if (props.onAction) {
        props.onAction(action);
      }
    }
    updateData() {
      let { props, state } = this;
      let oldData = this.data;
      let optionsData = this.computeOptionsData(props.optionOverrides, state.dynamicOptionOverrides, props.calendarApi);
      let currentViewData = this.computeCurrentViewData(state.currentViewType, optionsData, props.optionOverrides, state.dynamicOptionOverrides);
      let data = this.data = Object.assign(Object.assign(Object.assign({ nowManager: this.nowManager, viewTitle: this.buildTitle(state.dateProfile, currentViewData.options, optionsData.dateEnv), calendarApi: props.calendarApi, dispatch: this.dispatch, emitter: this.emitter, getCurrentData: this.getCurrentData }, optionsData), currentViewData), state);
      let changeHandlers = optionsData.pluginHooks.optionChangeHandlers;
      let oldCalendarOptions = oldData && oldData.calendarOptions;
      let newCalendarOptions = optionsData.calendarOptions;
      if (oldCalendarOptions && oldCalendarOptions !== newCalendarOptions) {
        if (oldCalendarOptions.timeZone !== newCalendarOptions.timeZone) {
          state.eventSources = data.eventSources = reduceEventSourcesNewTimeZone(data.eventSources, state.dateProfile, data);
          state.eventStore = data.eventStore = rezoneEventStoreDates(data.eventStore, oldData.dateEnv, data.dateEnv);
          state.renderableEventStore = data.renderableEventStore = rezoneEventStoreDates(data.renderableEventStore, oldData.dateEnv, data.dateEnv);
        }
        for (let optionName in changeHandlers) {
          if (this.optionsForHandling.indexOf(optionName) !== -1 || oldCalendarOptions[optionName] !== newCalendarOptions[optionName]) {
            changeHandlers[optionName](newCalendarOptions[optionName], data);
          }
        }
      }
      this.optionsForHandling = [];
      if (props.onData) {
        props.onData(data);
      }
    }
    computeOptionsData(optionOverrides, dynamicOptionOverrides, calendarApi) {
      if (!this.optionsForRefining.length && optionOverrides === this.stableOptionOverrides && dynamicOptionOverrides === this.stableDynamicOptionOverrides) {
        return this.stableCalendarOptionsData;
      }
      let { refinedOptions, pluginHooks, localeDefaults, availableLocaleData, extra } = this.processRawCalendarOptions(optionOverrides, dynamicOptionOverrides);
      warnUnknownOptions(extra);
      let dateEnv = this.buildDateEnv(refinedOptions.timeZone, refinedOptions.locale, refinedOptions.weekNumberCalculation, refinedOptions.firstDay, refinedOptions.weekText, pluginHooks, availableLocaleData, refinedOptions.defaultRangeSeparator);
      let viewSpecs = this.buildViewSpecs(pluginHooks.views, this.stableOptionOverrides, this.stableDynamicOptionOverrides, localeDefaults);
      let theme = this.buildTheme(refinedOptions, pluginHooks);
      let toolbarConfig = this.parseToolbars(refinedOptions, this.stableOptionOverrides, theme, viewSpecs, calendarApi);
      return this.stableCalendarOptionsData = {
        calendarOptions: refinedOptions,
        pluginHooks,
        dateEnv,
        viewSpecs,
        theme,
        toolbarConfig,
        localeDefaults,
        availableRawLocales: availableLocaleData.map
      };
    }
    processRawCalendarOptions(optionOverrides, dynamicOptionOverrides) {
      let { locales, locale } = mergeRawOptions([
        BASE_OPTION_DEFAULTS,
        optionOverrides,
        dynamicOptionOverrides
      ]);
      let availableLocaleData = this.organizeRawLocales(locales);
      let availableRawLocales = availableLocaleData.map;
      let localeDefaults = this.buildLocale(locale || availableLocaleData.defaultCode, availableRawLocales).options;
      let pluginHooks = this.buildPluginHooks(optionOverrides.plugins || [], globalPlugins);
      let refiners = this.currentCalendarOptionsRefiners = Object.assign(Object.assign(Object.assign(Object.assign(Object.assign({}, BASE_OPTION_REFINERS), CALENDAR_LISTENER_REFINERS), CALENDAR_OPTION_REFINERS), pluginHooks.listenerRefiners), pluginHooks.optionRefiners);
      let extra = {};
      let raw = mergeRawOptions([
        BASE_OPTION_DEFAULTS,
        localeDefaults,
        optionOverrides,
        dynamicOptionOverrides
      ]);
      let refined = {};
      let currentRaw = this.currentCalendarOptionsInput;
      let currentRefined = this.currentCalendarOptionsRefined;
      let anyChanges = false;
      for (let optionName in raw) {
        if (this.optionsForRefining.indexOf(optionName) === -1 && (raw[optionName] === currentRaw[optionName] || COMPLEX_OPTION_COMPARATORS[optionName] && optionName in currentRaw && COMPLEX_OPTION_COMPARATORS[optionName](currentRaw[optionName], raw[optionName]))) {
          refined[optionName] = currentRefined[optionName];
        } else if (refiners[optionName]) {
          refined[optionName] = refiners[optionName](raw[optionName]);
          anyChanges = true;
        } else {
          extra[optionName] = currentRaw[optionName];
        }
      }
      if (anyChanges) {
        this.currentCalendarOptionsInput = raw;
        this.currentCalendarOptionsRefined = refined;
        this.stableOptionOverrides = optionOverrides;
        this.stableDynamicOptionOverrides = dynamicOptionOverrides;
      }
      this.optionsForHandling.push(...this.optionsForRefining);
      this.optionsForRefining = [];
      return {
        rawOptions: this.currentCalendarOptionsInput,
        refinedOptions: this.currentCalendarOptionsRefined,
        pluginHooks,
        availableLocaleData,
        localeDefaults,
        extra
      };
    }
    _computeCurrentViewData(viewType, optionsData, optionOverrides, dynamicOptionOverrides) {
      let viewSpec = optionsData.viewSpecs[viewType];
      if (!viewSpec) {
        throw new Error(`viewType "${viewType}" is not available. Please make sure you've loaded all neccessary plugins`);
      }
      let { refinedOptions, extra } = this.processRawViewOptions(viewSpec, optionsData.pluginHooks, optionsData.localeDefaults, optionOverrides, dynamicOptionOverrides);
      warnUnknownOptions(extra);
      this.nowManager.handleInput(optionsData.dateEnv, refinedOptions.now);
      let dateProfileGenerator = this.buildDateProfileGenerator({
        dateProfileGeneratorClass: viewSpec.optionDefaults.dateProfileGeneratorClass,
        nowManager: this.nowManager,
        duration: viewSpec.duration,
        durationUnit: viewSpec.durationUnit,
        usesMinMaxTime: viewSpec.optionDefaults.usesMinMaxTime,
        dateEnv: optionsData.dateEnv,
        calendarApi: this.props.calendarApi,
        slotMinTime: refinedOptions.slotMinTime,
        slotMaxTime: refinedOptions.slotMaxTime,
        showNonCurrentDates: refinedOptions.showNonCurrentDates,
        dayCount: refinedOptions.dayCount,
        dateAlignment: refinedOptions.dateAlignment,
        dateIncrement: refinedOptions.dateIncrement,
        hiddenDays: refinedOptions.hiddenDays,
        weekends: refinedOptions.weekends,
        validRangeInput: refinedOptions.validRange,
        visibleRangeInput: refinedOptions.visibleRange,
        fixedWeekCount: refinedOptions.fixedWeekCount
      });
      let viewApi = this.buildViewApi(viewType, this.getCurrentData, optionsData.dateEnv);
      return { viewSpec, options: refinedOptions, dateProfileGenerator, viewApi };
    }
    processRawViewOptions(viewSpec, pluginHooks, localeDefaults, optionOverrides, dynamicOptionOverrides) {
      let raw = mergeRawOptions([
        BASE_OPTION_DEFAULTS,
        viewSpec.optionDefaults,
        localeDefaults,
        optionOverrides,
        viewSpec.optionOverrides,
        dynamicOptionOverrides
      ]);
      let refiners = Object.assign(Object.assign(Object.assign(Object.assign(Object.assign(Object.assign({}, BASE_OPTION_REFINERS), CALENDAR_LISTENER_REFINERS), CALENDAR_OPTION_REFINERS), VIEW_OPTION_REFINERS), pluginHooks.listenerRefiners), pluginHooks.optionRefiners);
      let refined = {};
      let currentRaw = this.currentViewOptionsInput;
      let currentRefined = this.currentViewOptionsRefined;
      let anyChanges = false;
      let extra = {};
      for (let optionName in raw) {
        if (raw[optionName] === currentRaw[optionName] || COMPLEX_OPTION_COMPARATORS[optionName] && COMPLEX_OPTION_COMPARATORS[optionName](raw[optionName], currentRaw[optionName])) {
          refined[optionName] = currentRefined[optionName];
        } else {
          if (raw[optionName] === this.currentCalendarOptionsInput[optionName] || COMPLEX_OPTION_COMPARATORS[optionName] && COMPLEX_OPTION_COMPARATORS[optionName](raw[optionName], this.currentCalendarOptionsInput[optionName])) {
            if (optionName in this.currentCalendarOptionsRefined) {
              refined[optionName] = this.currentCalendarOptionsRefined[optionName];
            }
          } else if (refiners[optionName]) {
            refined[optionName] = refiners[optionName](raw[optionName]);
          } else {
            extra[optionName] = raw[optionName];
          }
          anyChanges = true;
        }
      }
      if (anyChanges) {
        this.currentViewOptionsInput = raw;
        this.currentViewOptionsRefined = refined;
      }
      return {
        rawOptions: this.currentViewOptionsInput,
        refinedOptions: this.currentViewOptionsRefined,
        extra
      };
    }
  };
  function buildDateEnv$1(timeZone, explicitLocale, weekNumberCalculation, firstDay, weekText, pluginHooks, availableLocaleData, defaultSeparator) {
    let locale = buildLocale(explicitLocale || availableLocaleData.defaultCode, availableLocaleData.map);
    return new DateEnv({
      calendarSystem: "gregory",
      timeZone,
      namedTimeZoneImpl: pluginHooks.namedTimeZonedImpl,
      locale,
      weekNumberCalculation,
      firstDay,
      weekText,
      cmdFormatter: pluginHooks.cmdFormatter,
      defaultSeparator
    });
  }
  function buildTheme(options, pluginHooks) {
    let ThemeClass = pluginHooks.themeClasses[options.themeSystem] || StandardTheme;
    return new ThemeClass(options);
  }
  function buildDateProfileGenerator(props) {
    let DateProfileGeneratorClass = props.dateProfileGeneratorClass || DateProfileGenerator;
    return new DateProfileGeneratorClass(props);
  }
  function buildViewApi(type, getCurrentData, dateEnv) {
    return new ViewImpl(type, getCurrentData, dateEnv);
  }
  function buildEventUiBySource(eventSources) {
    return mapHash(eventSources, (eventSource) => eventSource.ui);
  }
  function buildEventUiBases(eventDefs, eventUiSingleBase, eventUiBySource) {
    let eventUiBases = { "": eventUiSingleBase };
    for (let defId in eventDefs) {
      let def = eventDefs[defId];
      if (def.sourceId && eventUiBySource[def.sourceId]) {
        eventUiBases[defId] = eventUiBySource[def.sourceId];
      }
    }
    return eventUiBases;
  }
  function buildViewUiProps(calendarContext) {
    let { options } = calendarContext;
    return {
      eventUiSingleBase: createEventUi({
        display: options.eventDisplay,
        editable: options.editable,
        startEditable: options.eventStartEditable,
        durationEditable: options.eventDurationEditable,
        constraint: options.eventConstraint,
        overlap: typeof options.eventOverlap === "boolean" ? options.eventOverlap : void 0,
        allow: options.eventAllow,
        backgroundColor: options.eventBackgroundColor,
        borderColor: options.eventBorderColor,
        textColor: options.eventTextColor,
        color: options.eventColor
      }, calendarContext),
      selectionConfig: createEventUi({
        constraint: options.selectConstraint,
        overlap: typeof options.selectOverlap === "boolean" ? options.selectOverlap : void 0,
        allow: options.selectAllow
      }, calendarContext)
    };
  }
  function computeIsLoading(state, context) {
    for (let isLoadingFunc of context.pluginHooks.isLoadingFuncs) {
      if (isLoadingFunc(state)) {
        return true;
      }
    }
    return false;
  }
  function parseContextBusinessHours(calendarContext) {
    return parseBusinessHours(calendarContext.options.businessHours, calendarContext);
  }
  function warnUnknownOptions(options, viewName) {
    for (let optionName in options) {
      console.warn(`Unknown option '${optionName}'` + (viewName ? ` for view '${viewName}'` : ""));
    }
  }
  var ToolbarSection = class extends BaseComponent {
    render() {
      let children = this.props.widgetGroups.map((widgetGroup) => this.renderWidgetGroup(widgetGroup));
      return y("div", { className: "fc-toolbar-chunk" }, ...children);
    }
    renderWidgetGroup(widgetGroup) {
      let { props } = this;
      let { theme } = this.context;
      let children = [];
      let isOnlyButtons = true;
      for (let widget of widgetGroup) {
        let { buttonName, buttonClick, buttonText, buttonIcon, buttonHint } = widget;
        if (buttonName === "title") {
          isOnlyButtons = false;
          children.push(y("h2", { className: "fc-toolbar-title", id: props.titleId }, props.title));
        } else {
          let isPressed = buttonName === props.activeButton;
          let isDisabled = !props.isTodayEnabled && buttonName === "today" || !props.isPrevEnabled && buttonName === "prev" || !props.isNextEnabled && buttonName === "next";
          let buttonClasses = [`fc-${buttonName}-button`, theme.getClass("button")];
          if (isPressed) {
            buttonClasses.push(theme.getClass("buttonActive"));
          }
          children.push(y("button", { type: "button", title: typeof buttonHint === "function" ? buttonHint(props.navUnit) : buttonHint, disabled: isDisabled, "aria-pressed": isPressed, className: buttonClasses.join(" "), onClick: buttonClick }, buttonText || (buttonIcon ? y("span", { className: buttonIcon, role: "img" }) : "")));
        }
      }
      if (children.length > 1) {
        let groupClassName = isOnlyButtons && theme.getClass("buttonGroup") || "";
        return y("div", { className: groupClassName }, ...children);
      }
      return children[0];
    }
  };
  var Toolbar = class extends BaseComponent {
    render() {
      let { model, extraClassName } = this.props;
      let forceLtr = false;
      let startContent;
      let endContent;
      let sectionWidgets = model.sectionWidgets;
      let centerContent = sectionWidgets.center;
      if (sectionWidgets.left) {
        forceLtr = true;
        startContent = sectionWidgets.left;
      } else {
        startContent = sectionWidgets.start;
      }
      if (sectionWidgets.right) {
        forceLtr = true;
        endContent = sectionWidgets.right;
      } else {
        endContent = sectionWidgets.end;
      }
      let classNames = [
        extraClassName || "",
        "fc-toolbar",
        forceLtr ? "fc-toolbar-ltr" : ""
      ];
      return y(
        "div",
        { className: classNames.join(" ") },
        this.renderSection("start", startContent || []),
        this.renderSection("center", centerContent || []),
        this.renderSection("end", endContent || [])
      );
    }
    renderSection(key, widgetGroups) {
      let { props } = this;
      return y(ToolbarSection, { key, widgetGroups, title: props.title, navUnit: props.navUnit, activeButton: props.activeButton, isTodayEnabled: props.isTodayEnabled, isPrevEnabled: props.isPrevEnabled, isNextEnabled: props.isNextEnabled, titleId: props.titleId });
    }
  };
  var ViewHarness = class extends BaseComponent {
    constructor() {
      super(...arguments);
      this.state = {
        availableWidth: null
      };
      this.handleEl = (el) => {
        this.el = el;
        setRef(this.props.elRef, el);
        this.updateAvailableWidth();
      };
      this.handleResize = () => {
        this.updateAvailableWidth();
      };
    }
    render() {
      let { props, state } = this;
      let { aspectRatio } = props;
      let classNames = [
        "fc-view-harness",
        aspectRatio || props.liquid || props.height ? "fc-view-harness-active" : "fc-view-harness-passive"
      ];
      let height = "";
      let paddingBottom = "";
      if (aspectRatio) {
        if (state.availableWidth !== null) {
          height = state.availableWidth / aspectRatio;
        } else {
          paddingBottom = `${1 / aspectRatio * 100}%`;
        }
      } else {
        height = props.height || "";
      }
      return y("div", { "aria-labelledby": props.labeledById, ref: this.handleEl, className: classNames.join(" "), style: { height, paddingBottom } }, props.children);
    }
    componentDidMount() {
      this.context.addResizeHandler(this.handleResize);
    }
    componentWillUnmount() {
      this.context.removeResizeHandler(this.handleResize);
    }
    updateAvailableWidth() {
      if (this.el && this.props.aspectRatio) {
        this.setState({ availableWidth: this.el.offsetWidth });
      }
    }
  };
  var EventClicking = class extends Interaction {
    constructor(settings) {
      super(settings);
      this.handleSegClick = (ev, segEl) => {
        let { component } = this;
        let { context } = component;
        let seg = getElSeg(segEl);
        if (seg && component.isValidSegDownEl(ev.target)) {
          let hasUrlContainer = elementClosest(ev.target, ".fc-event-forced-url");
          let url = hasUrlContainer ? hasUrlContainer.querySelector("a[href]").href : "";
          context.emitter.trigger("eventClick", {
            el: segEl,
            event: new EventImpl(component.context, seg.eventRange.def, seg.eventRange.instance),
            jsEvent: ev,
            view: context.viewApi
          });
          if (url && !ev.defaultPrevented) {
            window.location.href = url;
          }
        }
      };
      this.destroy = listenBySelector(
        settings.el,
        "click",
        ".fc-event",
        this.handleSegClick
      );
    }
  };
  var EventHovering = class extends Interaction {
    constructor(settings) {
      super(settings);
      this.handleEventElRemove = (el) => {
        if (el === this.currentSegEl) {
          this.handleSegLeave(null, this.currentSegEl);
        }
      };
      this.handleSegEnter = (ev, segEl) => {
        if (getElSeg(segEl)) {
          this.currentSegEl = segEl;
          this.triggerEvent("eventMouseEnter", ev, segEl);
        }
      };
      this.handleSegLeave = (ev, segEl) => {
        if (this.currentSegEl) {
          this.currentSegEl = null;
          this.triggerEvent("eventMouseLeave", ev, segEl);
        }
      };
      this.removeHoverListeners = listenToHoverBySelector(
        settings.el,
        ".fc-event",
        this.handleSegEnter,
        this.handleSegLeave
      );
    }
    destroy() {
      this.removeHoverListeners();
    }
    triggerEvent(publicEvName, ev, segEl) {
      let { component } = this;
      let { context } = component;
      let seg = getElSeg(segEl);
      if (!ev || component.isValidSegDownEl(ev.target)) {
        context.emitter.trigger(publicEvName, {
          el: segEl,
          event: new EventImpl(context, seg.eventRange.def, seg.eventRange.instance),
          jsEvent: ev,
          view: context.viewApi
        });
      }
    }
  };
  var CalendarContent = class extends PureComponent {
    constructor() {
      super(...arguments);
      this.buildViewContext = memoize(buildViewContext);
      this.buildViewPropTransformers = memoize(buildViewPropTransformers);
      this.buildToolbarProps = memoize(buildToolbarProps);
      this.headerRef = d();
      this.footerRef = d();
      this.interactionsStore = {};
      this.state = {
        viewLabelId: getUniqueDomId()
      };
      this.registerInteractiveComponent = (component, settingsInput) => {
        let settings = parseInteractionSettings(component, settingsInput);
        let DEFAULT_INTERACTIONS = [
          EventClicking,
          EventHovering
        ];
        let interactionClasses = DEFAULT_INTERACTIONS.concat(this.props.pluginHooks.componentInteractions);
        let interactions = interactionClasses.map((TheInteractionClass) => new TheInteractionClass(settings));
        this.interactionsStore[component.uid] = interactions;
        interactionSettingsStore[component.uid] = settings;
      };
      this.unregisterInteractiveComponent = (component) => {
        let listeners = this.interactionsStore[component.uid];
        if (listeners) {
          for (let listener of listeners) {
            listener.destroy();
          }
          delete this.interactionsStore[component.uid];
        }
        delete interactionSettingsStore[component.uid];
      };
      this.resizeRunner = new DelayedRunner(() => {
        this.props.emitter.trigger("_resize", true);
        this.props.emitter.trigger("windowResize", { view: this.props.viewApi });
      });
      this.handleWindowResize = (ev) => {
        let { options } = this.props;
        if (options.handleWindowResize && ev.target === window) {
          this.resizeRunner.request(options.windowResizeDelay);
        }
      };
    }
    render() {
      let { props } = this;
      let { toolbarConfig, options } = props;
      let viewVGrow = false;
      let viewHeight = "";
      let viewAspectRatio;
      if (props.isHeightAuto || props.forPrint) {
        viewHeight = "";
      } else if (options.height != null) {
        viewVGrow = true;
      } else if (options.contentHeight != null) {
        viewHeight = options.contentHeight;
      } else {
        viewAspectRatio = Math.max(options.aspectRatio, 0.5);
      }
      let viewContext = this.buildViewContext(props.viewSpec, props.viewApi, props.options, props.dateProfileGenerator, props.dateEnv, props.nowManager, props.theme, props.pluginHooks, props.dispatch, props.getCurrentData, props.emitter, props.calendarApi, this.registerInteractiveComponent, this.unregisterInteractiveComponent);
      let viewLabelId = toolbarConfig.header && toolbarConfig.header.hasTitle ? this.state.viewLabelId : void 0;
      return y(
        ViewContextType.Provider,
        { value: viewContext },
        y(NowTimer, { unit: "day" }, (nowDate) => {
          let toolbarProps = this.buildToolbarProps(props.viewSpec, props.dateProfile, props.dateProfileGenerator, props.currentDate, nowDate, props.viewTitle);
          return y(
            _,
            null,
            toolbarConfig.header && y(Toolbar, Object.assign({ ref: this.headerRef, extraClassName: "fc-header-toolbar", model: toolbarConfig.header, titleId: viewLabelId }, toolbarProps)),
            y(
              ViewHarness,
              { liquid: viewVGrow, height: viewHeight, aspectRatio: viewAspectRatio, labeledById: viewLabelId },
              this.renderView(props),
              this.buildAppendContent()
            ),
            toolbarConfig.footer && y(Toolbar, Object.assign({ ref: this.footerRef, extraClassName: "fc-footer-toolbar", model: toolbarConfig.footer, titleId: "" }, toolbarProps))
          );
        })
      );
    }
    componentDidMount() {
      let { props } = this;
      this.calendarInteractions = props.pluginHooks.calendarInteractions.map((CalendarInteractionClass) => new CalendarInteractionClass(props));
      window.addEventListener("resize", this.handleWindowResize);
      let { propSetHandlers } = props.pluginHooks;
      for (let propName in propSetHandlers) {
        propSetHandlers[propName](props[propName], props);
      }
    }
    componentDidUpdate(prevProps) {
      let { props } = this;
      let { propSetHandlers } = props.pluginHooks;
      for (let propName in propSetHandlers) {
        if (props[propName] !== prevProps[propName]) {
          propSetHandlers[propName](props[propName], props);
        }
      }
    }
    componentWillUnmount() {
      window.removeEventListener("resize", this.handleWindowResize);
      this.resizeRunner.clear();
      for (let interaction of this.calendarInteractions) {
        interaction.destroy();
      }
      this.props.emitter.trigger("_unmount");
    }
    buildAppendContent() {
      let { props } = this;
      let children = props.pluginHooks.viewContainerAppends.map((buildAppendContent) => buildAppendContent(props));
      return y(_, {}, ...children);
    }
    renderView(props) {
      let { pluginHooks } = props;
      let { viewSpec } = props;
      let viewProps = {
        dateProfile: props.dateProfile,
        businessHours: props.businessHours,
        eventStore: props.renderableEventStore,
        eventUiBases: props.eventUiBases,
        dateSelection: props.dateSelection,
        eventSelection: props.eventSelection,
        eventDrag: props.eventDrag,
        eventResize: props.eventResize,
        isHeightAuto: props.isHeightAuto,
        forPrint: props.forPrint
      };
      let transformers = this.buildViewPropTransformers(pluginHooks.viewPropsTransformers);
      for (let transformer of transformers) {
        Object.assign(viewProps, transformer.transform(viewProps, props));
      }
      let ViewComponent = viewSpec.component;
      return y(ViewComponent, Object.assign({}, viewProps));
    }
  };
  function buildToolbarProps(viewSpec, dateProfile, dateProfileGenerator, currentDate, now, title) {
    let todayInfo = dateProfileGenerator.build(now, void 0, false);
    let prevInfo = dateProfileGenerator.buildPrev(dateProfile, currentDate, false);
    let nextInfo = dateProfileGenerator.buildNext(dateProfile, currentDate, false);
    return {
      title,
      activeButton: viewSpec.type,
      navUnit: viewSpec.singleUnit,
      isTodayEnabled: todayInfo.isValid && !rangeContainsMarker(dateProfile.currentRange, now),
      isPrevEnabled: prevInfo.isValid,
      isNextEnabled: nextInfo.isValid
    };
  }
  function buildViewPropTransformers(theClasses) {
    return theClasses.map((TheClass) => new TheClass());
  }
  var Calendar = class extends CalendarImpl {
    constructor(el, optionOverrides = {}) {
      super();
      this.isRendering = false;
      this.isRendered = false;
      this.currentClassNames = [];
      this.customContentRenderId = 0;
      this.handleAction = (action) => {
        switch (action.type) {
          case "SET_EVENT_DRAG":
          case "SET_EVENT_RESIZE":
            this.renderRunner.tryDrain();
        }
      };
      this.handleData = (data) => {
        this.currentData = data;
        this.renderRunner.request(data.calendarOptions.rerenderDelay);
      };
      this.handleRenderRequest = () => {
        if (this.isRendering) {
          this.isRendered = true;
          let { currentData } = this;
          flushSync(() => {
            D(y(CalendarRoot, { options: currentData.calendarOptions, theme: currentData.theme, emitter: currentData.emitter }, (classNames, height, isHeightAuto, forPrint) => {
              this.setClassNames(classNames);
              this.setHeight(height);
              return y(
                RenderId.Provider,
                { value: this.customContentRenderId },
                y(CalendarContent, Object.assign({ isHeightAuto, forPrint }, currentData))
              );
            }), this.el);
          });
        } else if (this.isRendered) {
          this.isRendered = false;
          D(null, this.el);
          this.setClassNames([]);
          this.setHeight("");
        }
      };
      ensureElHasStyles(el);
      this.el = el;
      this.renderRunner = new DelayedRunner(this.handleRenderRequest);
      new CalendarDataManager({
        optionOverrides,
        calendarApi: this,
        onAction: this.handleAction,
        onData: this.handleData
      });
    }
    render() {
      let wasRendering = this.isRendering;
      if (!wasRendering) {
        this.isRendering = true;
      } else {
        this.customContentRenderId += 1;
      }
      this.renderRunner.request();
      if (wasRendering) {
        this.updateSize();
      }
    }
    destroy() {
      if (this.isRendering) {
        this.isRendering = false;
        this.renderRunner.request();
      }
    }
    updateSize() {
      flushSync(() => {
        super.updateSize();
      });
    }
    batchRendering(func) {
      this.renderRunner.pause("batchRendering");
      func();
      this.renderRunner.resume("batchRendering");
    }
    pauseRendering() {
      this.renderRunner.pause("pauseRendering");
    }
    resumeRendering() {
      this.renderRunner.resume("pauseRendering", true);
    }
    resetOptions(optionOverrides, changedOptionNames) {
      this.currentDataManager.resetOptions(optionOverrides, changedOptionNames);
    }
    setClassNames(classNames) {
      if (!isArraysEqual(classNames, this.currentClassNames)) {
        let { classList } = this.el;
        for (let className of this.currentClassNames) {
          classList.remove(className);
        }
        for (let className of classNames) {
          classList.add(className);
        }
        this.currentClassNames = classNames;
      }
    }
    setHeight(height) {
      applyStyleProp(this.el, "height", height);
    }
  };

  // ../ifitwala_ed/node_modules/@fullcalendar/daygrid/internal.js
  var TableView = class extends DateComponent {
    constructor() {
      super(...arguments);
      this.headerElRef = d();
    }
    renderSimpleLayout(headerRowContent, bodyContent) {
      let { props, context } = this;
      let sections = [];
      let stickyHeaderDates = getStickyHeaderDates(context.options);
      if (headerRowContent) {
        sections.push({
          type: "header",
          key: "header",
          isSticky: stickyHeaderDates,
          chunk: {
            elRef: this.headerElRef,
            tableClassName: "fc-col-header",
            rowContent: headerRowContent
          }
        });
      }
      sections.push({
        type: "body",
        key: "body",
        liquid: true,
        chunk: { content: bodyContent }
      });
      return y(
        ViewContainer,
        { elClasses: ["fc-daygrid"], viewSpec: context.viewSpec },
        y(SimpleScrollGrid, { liquid: !props.isHeightAuto && !props.forPrint, collapsibleWidth: props.forPrint, cols: [], sections })
      );
    }
    renderHScrollLayout(headerRowContent, bodyContent, colCnt, dayMinWidth) {
      let ScrollGrid = this.context.pluginHooks.scrollGridImpl;
      if (!ScrollGrid) {
        throw new Error("No ScrollGrid implementation");
      }
      let { props, context } = this;
      let stickyHeaderDates = !props.forPrint && getStickyHeaderDates(context.options);
      let stickyFooterScrollbar = !props.forPrint && getStickyFooterScrollbar(context.options);
      let sections = [];
      if (headerRowContent) {
        sections.push({
          type: "header",
          key: "header",
          isSticky: stickyHeaderDates,
          chunks: [{
            key: "main",
            elRef: this.headerElRef,
            tableClassName: "fc-col-header",
            rowContent: headerRowContent
          }]
        });
      }
      sections.push({
        type: "body",
        key: "body",
        liquid: true,
        chunks: [{
          key: "main",
          content: bodyContent
        }]
      });
      if (stickyFooterScrollbar) {
        sections.push({
          type: "footer",
          key: "footer",
          isSticky: true,
          chunks: [{
            key: "main",
            content: renderScrollShim
          }]
        });
      }
      return y(
        ViewContainer,
        { elClasses: ["fc-daygrid"], viewSpec: context.viewSpec },
        y(ScrollGrid, { liquid: !props.isHeightAuto && !props.forPrint, forPrint: props.forPrint, collapsibleWidth: props.forPrint, colGroups: [{ cols: [{ span: colCnt, minWidth: dayMinWidth }] }], sections })
      );
    }
  };
  function splitSegsByRow(segs, rowCnt) {
    let byRow = [];
    for (let i3 = 0; i3 < rowCnt; i3 += 1) {
      byRow[i3] = [];
    }
    for (let seg of segs) {
      byRow[seg.row].push(seg);
    }
    return byRow;
  }
  function splitSegsByFirstCol(segs, colCnt) {
    let byCol = [];
    for (let i3 = 0; i3 < colCnt; i3 += 1) {
      byCol[i3] = [];
    }
    for (let seg of segs) {
      byCol[seg.firstCol].push(seg);
    }
    return byCol;
  }
  function splitInteractionByRow(ui, rowCnt) {
    let byRow = [];
    if (!ui) {
      for (let i3 = 0; i3 < rowCnt; i3 += 1) {
        byRow[i3] = null;
      }
    } else {
      for (let i3 = 0; i3 < rowCnt; i3 += 1) {
        byRow[i3] = {
          affectedInstances: ui.affectedInstances,
          isEvent: ui.isEvent,
          segs: []
        };
      }
      for (let seg of ui.segs) {
        byRow[seg.row].segs.push(seg);
      }
    }
    return byRow;
  }
  var DEFAULT_TABLE_EVENT_TIME_FORMAT = createFormatter({
    hour: "numeric",
    minute: "2-digit",
    omitZeroMinute: true,
    meridiem: "narrow"
  });
  function hasListItemDisplay(seg) {
    let { display } = seg.eventRange.ui;
    return display === "list-item" || display === "auto" && !seg.eventRange.def.allDay && seg.firstCol === seg.lastCol && seg.isStart && seg.isEnd;
  }
  var TableBlockEvent = class extends BaseComponent {
    render() {
      let { props } = this;
      return y(StandardEvent, Object.assign({}, props, { elClasses: ["fc-daygrid-event", "fc-daygrid-block-event", "fc-h-event"], defaultTimeFormat: DEFAULT_TABLE_EVENT_TIME_FORMAT, defaultDisplayEventEnd: props.defaultDisplayEventEnd, disableResizing: !props.seg.eventRange.def.allDay }));
    }
  };
  var TableListItemEvent = class extends BaseComponent {
    render() {
      let { props, context } = this;
      let { options } = context;
      let { seg } = props;
      let timeFormat = options.eventTimeFormat || DEFAULT_TABLE_EVENT_TIME_FORMAT;
      let timeText = buildSegTimeText(seg, timeFormat, context, true, props.defaultDisplayEventEnd);
      return y(EventContainer, Object.assign({}, props, { elTag: "a", elClasses: ["fc-daygrid-event", "fc-daygrid-dot-event"], elAttrs: getSegAnchorAttrs(props.seg, context), defaultGenerator: renderInnerContent2, timeText, isResizing: false, isDateSelecting: false }));
    }
  };
  function renderInnerContent2(renderProps) {
    return y(
      _,
      null,
      y("div", { className: "fc-daygrid-event-dot", style: { borderColor: renderProps.borderColor || renderProps.backgroundColor } }),
      renderProps.timeText && y("div", { className: "fc-event-time" }, renderProps.timeText),
      y("div", { className: "fc-event-title" }, renderProps.event.title || y(_, null, "\xA0"))
    );
  }
  var TableCellMoreLink = class extends BaseComponent {
    constructor() {
      super(...arguments);
      this.compileSegs = memoize(compileSegs);
    }
    render() {
      let { props } = this;
      let { allSegs, invisibleSegs } = this.compileSegs(props.singlePlacements);
      return y(MoreLinkContainer, { elClasses: ["fc-daygrid-more-link"], dateProfile: props.dateProfile, todayRange: props.todayRange, allDayDate: props.allDayDate, moreCnt: props.moreCnt, allSegs, hiddenSegs: invisibleSegs, alignmentElRef: props.alignmentElRef, alignGridTop: props.alignGridTop, extraDateSpan: props.extraDateSpan, popoverContent: () => {
        let isForcedInvisible = (props.eventDrag ? props.eventDrag.affectedInstances : null) || (props.eventResize ? props.eventResize.affectedInstances : null) || {};
        return y(_, null, allSegs.map((seg) => {
          let instanceId = seg.eventRange.instance.instanceId;
          return y("div", { className: "fc-daygrid-event-harness", key: instanceId, style: {
            visibility: isForcedInvisible[instanceId] ? "hidden" : ""
          } }, hasListItemDisplay(seg) ? y(TableListItemEvent, Object.assign({ seg, isDragging: false, isSelected: instanceId === props.eventSelection, defaultDisplayEventEnd: false }, getSegMeta(seg, props.todayRange))) : y(TableBlockEvent, Object.assign({ seg, isDragging: false, isResizing: false, isDateSelecting: false, isSelected: instanceId === props.eventSelection, defaultDisplayEventEnd: false }, getSegMeta(seg, props.todayRange))));
        }));
      } });
    }
  };
  function compileSegs(singlePlacements) {
    let allSegs = [];
    let invisibleSegs = [];
    for (let placement of singlePlacements) {
      allSegs.push(placement.seg);
      if (!placement.isVisible) {
        invisibleSegs.push(placement.seg);
      }
    }
    return { allSegs, invisibleSegs };
  }
  var DEFAULT_WEEK_NUM_FORMAT = createFormatter({ week: "narrow" });
  var TableCell = class extends DateComponent {
    constructor() {
      super(...arguments);
      this.rootElRef = d();
      this.state = {
        dayNumberId: getUniqueDomId()
      };
      this.handleRootEl = (el) => {
        setRef(this.rootElRef, el);
        setRef(this.props.elRef, el);
      };
    }
    render() {
      let { context, props, state, rootElRef } = this;
      let { options, dateEnv } = context;
      let { date, dateProfile } = props;
      const isMonthStart = props.showDayNumber && shouldDisplayMonthStart(date, dateProfile.currentRange, dateEnv);
      return y(DayCellContainer, { elTag: "td", elRef: this.handleRootEl, elClasses: [
        "fc-daygrid-day",
        ...props.extraClassNames || []
      ], elAttrs: Object.assign(Object.assign(Object.assign({}, props.extraDataAttrs), props.showDayNumber ? { "aria-labelledby": state.dayNumberId } : {}), { role: "gridcell" }), defaultGenerator: renderTopInner, date, dateProfile, todayRange: props.todayRange, showDayNumber: props.showDayNumber, isMonthStart, extraRenderProps: props.extraRenderProps }, (InnerContent, renderProps) => y(
        "div",
        { ref: props.innerElRef, className: "fc-daygrid-day-frame fc-scrollgrid-sync-inner", style: { minHeight: props.minHeight } },
        props.showWeekNumber && y(WeekNumberContainer, { elTag: "a", elClasses: ["fc-daygrid-week-number"], elAttrs: buildNavLinkAttrs(context, date, "week"), date, defaultFormat: DEFAULT_WEEK_NUM_FORMAT }),
        !renderProps.isDisabled && (props.showDayNumber || hasCustomDayCellContent(options) || props.forceDayTop) ? y(
          "div",
          { className: "fc-daygrid-day-top" },
          y(InnerContent, { elTag: "a", elClasses: [
            "fc-daygrid-day-number",
            isMonthStart && "fc-daygrid-month-start"
          ], elAttrs: Object.assign(Object.assign({}, buildNavLinkAttrs(context, date)), { id: state.dayNumberId }) })
        ) : props.showDayNumber ? y(
          "div",
          { className: "fc-daygrid-day-top", style: { visibility: "hidden" } },
          y("a", { className: "fc-daygrid-day-number" }, "\xA0")
        ) : void 0,
        y(
          "div",
          { className: "fc-daygrid-day-events", ref: props.fgContentElRef },
          props.fgContent,
          y(
            "div",
            { className: "fc-daygrid-day-bottom", style: { marginTop: props.moreMarginTop } },
            y(TableCellMoreLink, { allDayDate: date, singlePlacements: props.singlePlacements, moreCnt: props.moreCnt, alignmentElRef: rootElRef, alignGridTop: !props.showDayNumber, extraDateSpan: props.extraDateSpan, dateProfile: props.dateProfile, eventSelection: props.eventSelection, eventDrag: props.eventDrag, eventResize: props.eventResize, todayRange: props.todayRange })
          )
        ),
        y("div", { className: "fc-daygrid-day-bg" }, props.bgContent)
      ));
    }
  };
  function renderTopInner(props) {
    return props.dayNumberText || y(_, null, "\xA0");
  }
  function shouldDisplayMonthStart(date, currentRange, dateEnv) {
    const { start: currentStart, end: currentEnd } = currentRange;
    const currentEndIncl = addMs(currentEnd, -1);
    const currentFirstYear = dateEnv.getYear(currentStart);
    const currentFirstMonth = dateEnv.getMonth(currentStart);
    const currentLastYear = dateEnv.getYear(currentEndIncl);
    const currentLastMonth = dateEnv.getMonth(currentEndIncl);
    return !(currentFirstYear === currentLastYear && currentFirstMonth === currentLastMonth) && Boolean(
      date.valueOf() === currentStart.valueOf() || dateEnv.getDay(date) === 1 && date.valueOf() < currentEnd.valueOf()
    );
  }
  function generateSegKey(seg) {
    return seg.eventRange.instance.instanceId + ":" + seg.firstCol;
  }
  function generateSegUid(seg) {
    return generateSegKey(seg) + ":" + seg.lastCol;
  }
  function computeFgSegPlacement(segs, dayMaxEvents, dayMaxEventRows, strictOrder, segHeights, maxContentHeight, cells) {
    let hierarchy = new DayGridSegHierarchy((segEntry) => {
      let segUid = segs[segEntry.index].eventRange.instance.instanceId + ":" + segEntry.span.start + ":" + (segEntry.span.end - 1);
      return segHeights[segUid] || 1;
    });
    hierarchy.allowReslicing = true;
    hierarchy.strictOrder = strictOrder;
    if (dayMaxEvents === true || dayMaxEventRows === true) {
      hierarchy.maxCoord = maxContentHeight;
      hierarchy.hiddenConsumes = true;
    } else if (typeof dayMaxEvents === "number") {
      hierarchy.maxStackCnt = dayMaxEvents;
    } else if (typeof dayMaxEventRows === "number") {
      hierarchy.maxStackCnt = dayMaxEventRows;
      hierarchy.hiddenConsumes = true;
    }
    let segInputs = [];
    let unknownHeightSegs = [];
    for (let i3 = 0; i3 < segs.length; i3 += 1) {
      let seg = segs[i3];
      let segUid = generateSegUid(seg);
      let eventHeight = segHeights[segUid];
      if (eventHeight != null) {
        segInputs.push({
          index: i3,
          span: {
            start: seg.firstCol,
            end: seg.lastCol + 1
          }
        });
      } else {
        unknownHeightSegs.push(seg);
      }
    }
    let hiddenEntries = hierarchy.addSegs(segInputs);
    let segRects = hierarchy.toRects();
    let { singleColPlacements, multiColPlacements, leftoverMargins } = placeRects(segRects, segs, cells);
    let moreCnts = [];
    let moreMarginTops = [];
    for (let seg of unknownHeightSegs) {
      multiColPlacements[seg.firstCol].push({
        seg,
        isVisible: false,
        isAbsolute: true,
        absoluteTop: 0,
        marginTop: 0
      });
      for (let col = seg.firstCol; col <= seg.lastCol; col += 1) {
        singleColPlacements[col].push({
          seg: resliceSeg(seg, col, col + 1, cells),
          isVisible: false,
          isAbsolute: false,
          absoluteTop: 0,
          marginTop: 0
        });
      }
    }
    for (let col = 0; col < cells.length; col += 1) {
      moreCnts.push(0);
    }
    for (let hiddenEntry of hiddenEntries) {
      let seg = segs[hiddenEntry.index];
      let hiddenSpan = hiddenEntry.span;
      multiColPlacements[hiddenSpan.start].push({
        seg: resliceSeg(seg, hiddenSpan.start, hiddenSpan.end, cells),
        isVisible: false,
        isAbsolute: true,
        absoluteTop: 0,
        marginTop: 0
      });
      for (let col = hiddenSpan.start; col < hiddenSpan.end; col += 1) {
        moreCnts[col] += 1;
        singleColPlacements[col].push({
          seg: resliceSeg(seg, col, col + 1, cells),
          isVisible: false,
          isAbsolute: false,
          absoluteTop: 0,
          marginTop: 0
        });
      }
    }
    for (let col = 0; col < cells.length; col += 1) {
      moreMarginTops.push(leftoverMargins[col]);
    }
    return { singleColPlacements, multiColPlacements, moreCnts, moreMarginTops };
  }
  function placeRects(allRects, segs, cells) {
    let rectsByEachCol = groupRectsByEachCol(allRects, cells.length);
    let singleColPlacements = [];
    let multiColPlacements = [];
    let leftoverMargins = [];
    for (let col = 0; col < cells.length; col += 1) {
      let rects = rectsByEachCol[col];
      let singlePlacements = [];
      let currentHeight = 0;
      let currentMarginTop = 0;
      for (let rect of rects) {
        let seg = segs[rect.index];
        singlePlacements.push({
          seg: resliceSeg(seg, col, col + 1, cells),
          isVisible: true,
          isAbsolute: false,
          absoluteTop: rect.levelCoord,
          marginTop: rect.levelCoord - currentHeight
        });
        currentHeight = rect.levelCoord + rect.thickness;
      }
      let multiPlacements = [];
      currentHeight = 0;
      currentMarginTop = 0;
      for (let rect of rects) {
        let seg = segs[rect.index];
        let isAbsolute = rect.span.end - rect.span.start > 1;
        let isFirstCol = rect.span.start === col;
        currentMarginTop += rect.levelCoord - currentHeight;
        currentHeight = rect.levelCoord + rect.thickness;
        if (isAbsolute) {
          currentMarginTop += rect.thickness;
          if (isFirstCol) {
            multiPlacements.push({
              seg: resliceSeg(seg, rect.span.start, rect.span.end, cells),
              isVisible: true,
              isAbsolute: true,
              absoluteTop: rect.levelCoord,
              marginTop: 0
            });
          }
        } else if (isFirstCol) {
          multiPlacements.push({
            seg: resliceSeg(seg, rect.span.start, rect.span.end, cells),
            isVisible: true,
            isAbsolute: false,
            absoluteTop: rect.levelCoord,
            marginTop: currentMarginTop
          });
          currentMarginTop = 0;
        }
      }
      singleColPlacements.push(singlePlacements);
      multiColPlacements.push(multiPlacements);
      leftoverMargins.push(currentMarginTop);
    }
    return { singleColPlacements, multiColPlacements, leftoverMargins };
  }
  function groupRectsByEachCol(rects, colCnt) {
    let rectsByEachCol = [];
    for (let col = 0; col < colCnt; col += 1) {
      rectsByEachCol.push([]);
    }
    for (let rect of rects) {
      for (let col = rect.span.start; col < rect.span.end; col += 1) {
        rectsByEachCol[col].push(rect);
      }
    }
    return rectsByEachCol;
  }
  function resliceSeg(seg, spanStart, spanEnd, cells) {
    if (seg.firstCol === spanStart && seg.lastCol === spanEnd - 1) {
      return seg;
    }
    let eventRange = seg.eventRange;
    let origRange = eventRange.range;
    let slicedRange = intersectRanges(origRange, {
      start: cells[spanStart].date,
      end: addDays(cells[spanEnd - 1].date, 1)
    });
    return Object.assign(Object.assign({}, seg), { firstCol: spanStart, lastCol: spanEnd - 1, eventRange: {
      def: eventRange.def,
      ui: Object.assign(Object.assign({}, eventRange.ui), { durationEditable: false }),
      instance: eventRange.instance,
      range: slicedRange
    }, isStart: seg.isStart && slicedRange.start.valueOf() === origRange.start.valueOf(), isEnd: seg.isEnd && slicedRange.end.valueOf() === origRange.end.valueOf() });
  }
  var DayGridSegHierarchy = class extends SegHierarchy {
    constructor() {
      super(...arguments);
      this.hiddenConsumes = false;
      this.forceHidden = {};
    }
    addSegs(segInputs) {
      const hiddenSegs = super.addSegs(segInputs);
      const { entriesByLevel } = this;
      const excludeHidden = (entry) => !this.forceHidden[buildEntryKey(entry)];
      for (let level = 0; level < entriesByLevel.length; level += 1) {
        entriesByLevel[level] = entriesByLevel[level].filter(excludeHidden);
      }
      return hiddenSegs;
    }
    handleInvalidInsertion(insertion, entry, hiddenEntries) {
      const { entriesByLevel, forceHidden } = this;
      const { touchingEntry, touchingLevel, touchingLateral } = insertion;
      if (this.hiddenConsumes && touchingEntry) {
        const touchingEntryId = buildEntryKey(touchingEntry);
        if (!forceHidden[touchingEntryId]) {
          if (this.allowReslicing) {
            const hiddenEntry = Object.assign(Object.assign({}, touchingEntry), { span: intersectSpans(touchingEntry.span, entry.span) });
            const hiddenEntryId = buildEntryKey(hiddenEntry);
            forceHidden[hiddenEntryId] = true;
            entriesByLevel[touchingLevel][touchingLateral] = hiddenEntry;
            hiddenEntries.push(hiddenEntry);
            this.splitEntry(touchingEntry, entry, hiddenEntries);
          } else {
            forceHidden[touchingEntryId] = true;
            hiddenEntries.push(touchingEntry);
          }
        }
      }
      super.handleInvalidInsertion(insertion, entry, hiddenEntries);
    }
  };
  var TableRow = class extends DateComponent {
    constructor() {
      super(...arguments);
      this.cellElRefs = new RefMap();
      this.frameElRefs = new RefMap();
      this.fgElRefs = new RefMap();
      this.segHarnessRefs = new RefMap();
      this.rootElRef = d();
      this.state = {
        framePositions: null,
        maxContentHeight: null,
        segHeights: {}
      };
      this.handleResize = (isForced) => {
        if (isForced) {
          this.updateSizing(true);
        }
      };
    }
    render() {
      let { props, state, context } = this;
      let { options } = context;
      let colCnt = props.cells.length;
      let businessHoursByCol = splitSegsByFirstCol(props.businessHourSegs, colCnt);
      let bgEventSegsByCol = splitSegsByFirstCol(props.bgEventSegs, colCnt);
      let highlightSegsByCol = splitSegsByFirstCol(this.getHighlightSegs(), colCnt);
      let mirrorSegsByCol = splitSegsByFirstCol(this.getMirrorSegs(), colCnt);
      let { singleColPlacements, multiColPlacements, moreCnts, moreMarginTops } = computeFgSegPlacement(sortEventSegs(props.fgEventSegs, options.eventOrder), props.dayMaxEvents, props.dayMaxEventRows, options.eventOrderStrict, state.segHeights, state.maxContentHeight, props.cells);
      let isForcedInvisible = props.eventDrag && props.eventDrag.affectedInstances || props.eventResize && props.eventResize.affectedInstances || {};
      return y(
        "tr",
        { ref: this.rootElRef, role: "row" },
        props.renderIntro && props.renderIntro(),
        props.cells.map((cell, col) => {
          let normalFgNodes = this.renderFgSegs(col, props.forPrint ? singleColPlacements[col] : multiColPlacements[col], props.todayRange, isForcedInvisible);
          let mirrorFgNodes = this.renderFgSegs(col, buildMirrorPlacements(mirrorSegsByCol[col], multiColPlacements), props.todayRange, {}, Boolean(props.eventDrag), Boolean(props.eventResize), false);
          return y(TableCell, { key: cell.key, elRef: this.cellElRefs.createRef(cell.key), innerElRef: this.frameElRefs.createRef(cell.key), dateProfile: props.dateProfile, date: cell.date, showDayNumber: props.showDayNumbers, showWeekNumber: props.showWeekNumbers && col === 0, forceDayTop: props.showWeekNumbers, todayRange: props.todayRange, eventSelection: props.eventSelection, eventDrag: props.eventDrag, eventResize: props.eventResize, extraRenderProps: cell.extraRenderProps, extraDataAttrs: cell.extraDataAttrs, extraClassNames: cell.extraClassNames, extraDateSpan: cell.extraDateSpan, moreCnt: moreCnts[col], moreMarginTop: moreMarginTops[col], singlePlacements: singleColPlacements[col], fgContentElRef: this.fgElRefs.createRef(cell.key), fgContent: y(
            _,
            null,
            y(_, null, normalFgNodes),
            y(_, null, mirrorFgNodes)
          ), bgContent: y(
            _,
            null,
            this.renderFillSegs(highlightSegsByCol[col], "highlight"),
            this.renderFillSegs(businessHoursByCol[col], "non-business"),
            this.renderFillSegs(bgEventSegsByCol[col], "bg-event")
          ), minHeight: props.cellMinHeight });
        })
      );
    }
    componentDidMount() {
      this.updateSizing(true);
      this.context.addResizeHandler(this.handleResize);
    }
    componentDidUpdate(prevProps, prevState) {
      let currentProps = this.props;
      this.updateSizing(!isPropsEqual(prevProps, currentProps));
    }
    componentWillUnmount() {
      this.context.removeResizeHandler(this.handleResize);
    }
    getHighlightSegs() {
      let { props } = this;
      if (props.eventDrag && props.eventDrag.segs.length) {
        return props.eventDrag.segs;
      }
      if (props.eventResize && props.eventResize.segs.length) {
        return props.eventResize.segs;
      }
      return props.dateSelectionSegs;
    }
    getMirrorSegs() {
      let { props } = this;
      if (props.eventResize && props.eventResize.segs.length) {
        return props.eventResize.segs;
      }
      return [];
    }
    renderFgSegs(col, segPlacements, todayRange, isForcedInvisible, isDragging, isResizing, isDateSelecting) {
      let { context } = this;
      let { eventSelection } = this.props;
      let { framePositions } = this.state;
      let defaultDisplayEventEnd = this.props.cells.length === 1;
      let isMirror = isDragging || isResizing || isDateSelecting;
      let nodes = [];
      if (framePositions) {
        for (let placement of segPlacements) {
          let { seg } = placement;
          let { instanceId } = seg.eventRange.instance;
          let isVisible = placement.isVisible && !isForcedInvisible[instanceId];
          let isAbsolute = placement.isAbsolute;
          let left = "";
          let right = "";
          if (isAbsolute) {
            if (context.isRtl) {
              right = 0;
              left = framePositions.lefts[seg.lastCol] - framePositions.lefts[seg.firstCol];
            } else {
              left = 0;
              right = framePositions.rights[seg.firstCol] - framePositions.rights[seg.lastCol];
            }
          }
          nodes.push(y("div", { className: "fc-daygrid-event-harness" + (isAbsolute ? " fc-daygrid-event-harness-abs" : ""), key: generateSegKey(seg), ref: isMirror ? null : this.segHarnessRefs.createRef(generateSegUid(seg)), style: {
            visibility: isVisible ? "" : "hidden",
            marginTop: isAbsolute ? "" : placement.marginTop,
            top: isAbsolute ? placement.absoluteTop : "",
            left,
            right
          } }, hasListItemDisplay(seg) ? y(TableListItemEvent, Object.assign({ seg, isDragging, isSelected: instanceId === eventSelection, defaultDisplayEventEnd }, getSegMeta(seg, todayRange))) : y(TableBlockEvent, Object.assign({ seg, isDragging, isResizing, isDateSelecting, isSelected: instanceId === eventSelection, defaultDisplayEventEnd }, getSegMeta(seg, todayRange)))));
        }
      }
      return nodes;
    }
    renderFillSegs(segs, fillType) {
      let { isRtl } = this.context;
      let { todayRange } = this.props;
      let { framePositions } = this.state;
      let nodes = [];
      if (framePositions) {
        for (let seg of segs) {
          let leftRightCss = isRtl ? {
            right: 0,
            left: framePositions.lefts[seg.lastCol] - framePositions.lefts[seg.firstCol]
          } : {
            left: 0,
            right: framePositions.rights[seg.firstCol] - framePositions.rights[seg.lastCol]
          };
          nodes.push(y("div", { key: buildEventRangeKey(seg.eventRange), className: "fc-daygrid-bg-harness", style: leftRightCss }, fillType === "bg-event" ? y(BgEvent, Object.assign({ seg }, getSegMeta(seg, todayRange))) : renderFill(fillType)));
        }
      }
      return y(_, {}, ...nodes);
    }
    updateSizing(isExternalSizingChange) {
      let { props, state, frameElRefs } = this;
      if (!props.forPrint && props.clientWidth !== null) {
        if (isExternalSizingChange) {
          let frameEls = props.cells.map((cell) => frameElRefs.currentMap[cell.key]);
          if (frameEls.length) {
            let originEl = this.rootElRef.current;
            let newPositionCache = new PositionCache(
              originEl,
              frameEls,
              true,
              false
            );
            if (!state.framePositions || !state.framePositions.similarTo(newPositionCache)) {
              this.setState({
                framePositions: new PositionCache(
                  originEl,
                  frameEls,
                  true,
                  false
                )
              });
            }
          }
        }
        const oldSegHeights = this.state.segHeights;
        const newSegHeights = this.querySegHeights();
        const limitByContentHeight = props.dayMaxEvents === true || props.dayMaxEventRows === true;
        this.safeSetState({
          segHeights: Object.assign(Object.assign({}, oldSegHeights), newSegHeights),
          maxContentHeight: limitByContentHeight ? this.computeMaxContentHeight() : null
        });
      }
    }
    querySegHeights() {
      let segElMap = this.segHarnessRefs.currentMap;
      let segHeights = {};
      for (let segUid in segElMap) {
        let height = Math.round(segElMap[segUid].getBoundingClientRect().height);
        segHeights[segUid] = Math.max(segHeights[segUid] || 0, height);
      }
      return segHeights;
    }
    computeMaxContentHeight() {
      let firstKey = this.props.cells[0].key;
      let cellEl = this.cellElRefs.currentMap[firstKey];
      let fcContainerEl = this.fgElRefs.currentMap[firstKey];
      return cellEl.getBoundingClientRect().bottom - fcContainerEl.getBoundingClientRect().top;
    }
    getCellEls() {
      let elMap = this.cellElRefs.currentMap;
      return this.props.cells.map((cell) => elMap[cell.key]);
    }
  };
  TableRow.addStateEquality({
    segHeights: isPropsEqual
  });
  function buildMirrorPlacements(mirrorSegs, colPlacements) {
    if (!mirrorSegs.length) {
      return [];
    }
    let topsByInstanceId = buildAbsoluteTopHash(colPlacements);
    return mirrorSegs.map((seg) => ({
      seg,
      isVisible: true,
      isAbsolute: true,
      absoluteTop: topsByInstanceId[seg.eventRange.instance.instanceId],
      marginTop: 0
    }));
  }
  function buildAbsoluteTopHash(colPlacements) {
    let topsByInstanceId = {};
    for (let placements of colPlacements) {
      for (let placement of placements) {
        topsByInstanceId[placement.seg.eventRange.instance.instanceId] = placement.absoluteTop;
      }
    }
    return topsByInstanceId;
  }
  var TableRows = class extends DateComponent {
    constructor() {
      super(...arguments);
      this.splitBusinessHourSegs = memoize(splitSegsByRow);
      this.splitBgEventSegs = memoize(splitSegsByRow);
      this.splitFgEventSegs = memoize(splitSegsByRow);
      this.splitDateSelectionSegs = memoize(splitSegsByRow);
      this.splitEventDrag = memoize(splitInteractionByRow);
      this.splitEventResize = memoize(splitInteractionByRow);
      this.rowRefs = new RefMap();
    }
    render() {
      let { props, context } = this;
      let rowCnt = props.cells.length;
      let businessHourSegsByRow = this.splitBusinessHourSegs(props.businessHourSegs, rowCnt);
      let bgEventSegsByRow = this.splitBgEventSegs(props.bgEventSegs, rowCnt);
      let fgEventSegsByRow = this.splitFgEventSegs(props.fgEventSegs, rowCnt);
      let dateSelectionSegsByRow = this.splitDateSelectionSegs(props.dateSelectionSegs, rowCnt);
      let eventDragByRow = this.splitEventDrag(props.eventDrag, rowCnt);
      let eventResizeByRow = this.splitEventResize(props.eventResize, rowCnt);
      let cellMinHeight = rowCnt >= 7 && props.clientWidth ? props.clientWidth / context.options.aspectRatio / 6 : null;
      return y(NowTimer, { unit: "day" }, (nowDate, todayRange) => y(_, null, props.cells.map((cells, row) => y(TableRow, {
        ref: this.rowRefs.createRef(row),
        key: cells.length ? cells[0].date.toISOString() : row,
        showDayNumbers: rowCnt > 1,
        showWeekNumbers: props.showWeekNumbers,
        todayRange,
        dateProfile: props.dateProfile,
        cells,
        renderIntro: props.renderRowIntro,
        businessHourSegs: businessHourSegsByRow[row],
        eventSelection: props.eventSelection,
        bgEventSegs: bgEventSegsByRow[row].filter(isSegAllDay),
        fgEventSegs: fgEventSegsByRow[row],
        dateSelectionSegs: dateSelectionSegsByRow[row],
        eventDrag: eventDragByRow[row],
        eventResize: eventResizeByRow[row],
        dayMaxEvents: props.dayMaxEvents,
        dayMaxEventRows: props.dayMaxEventRows,
        clientWidth: props.clientWidth,
        clientHeight: props.clientHeight,
        cellMinHeight,
        forPrint: props.forPrint
      }))));
    }
    componentDidMount() {
      this.registerInteractiveComponent();
    }
    componentDidUpdate() {
      this.registerInteractiveComponent();
    }
    registerInteractiveComponent() {
      if (!this.rootEl) {
        const firstCellEl = this.rowRefs.currentMap[0].getCellEls()[0];
        const rootEl = firstCellEl ? firstCellEl.closest(".fc-daygrid-body") : null;
        if (rootEl) {
          this.rootEl = rootEl;
          this.context.registerInteractiveComponent(this, {
            el: rootEl,
            isHitComboAllowed: this.props.isHitComboAllowed
          });
        }
      }
    }
    componentWillUnmount() {
      if (this.rootEl) {
        this.context.unregisterInteractiveComponent(this);
        this.rootEl = null;
      }
    }
    prepareHits() {
      this.rowPositions = new PositionCache(
        this.rootEl,
        this.rowRefs.collect().map((rowObj) => rowObj.getCellEls()[0]),
        false,
        true
      );
      this.colPositions = new PositionCache(
        this.rootEl,
        this.rowRefs.currentMap[0].getCellEls(),
        true,
        false
      );
    }
    queryHit(positionLeft, positionTop) {
      let { colPositions, rowPositions } = this;
      let col = colPositions.leftToIndex(positionLeft);
      let row = rowPositions.topToIndex(positionTop);
      if (row != null && col != null) {
        let cell = this.props.cells[row][col];
        return {
          dateProfile: this.props.dateProfile,
          dateSpan: Object.assign({ range: this.getCellRange(row, col), allDay: true }, cell.extraDateSpan),
          dayEl: this.getCellEl(row, col),
          rect: {
            left: colPositions.lefts[col],
            right: colPositions.rights[col],
            top: rowPositions.tops[row],
            bottom: rowPositions.bottoms[row]
          },
          layer: 0
        };
      }
      return null;
    }
    getCellEl(row, col) {
      return this.rowRefs.currentMap[row].getCellEls()[col];
    }
    getCellRange(row, col) {
      let start = this.props.cells[row][col].date;
      let end = addDays(start, 1);
      return { start, end };
    }
  };
  function isSegAllDay(seg) {
    return seg.eventRange.def.allDay;
  }
  var Table = class extends DateComponent {
    constructor() {
      super(...arguments);
      this.elRef = d();
      this.needsScrollReset = false;
    }
    render() {
      let { props } = this;
      let { dayMaxEventRows, dayMaxEvents, expandRows } = props;
      let limitViaBalanced = dayMaxEvents === true || dayMaxEventRows === true;
      if (limitViaBalanced && !expandRows) {
        limitViaBalanced = false;
        dayMaxEventRows = null;
        dayMaxEvents = null;
      }
      let classNames = [
        "fc-daygrid-body",
        limitViaBalanced ? "fc-daygrid-body-balanced" : "fc-daygrid-body-unbalanced",
        expandRows ? "" : "fc-daygrid-body-natural"
      ];
      return y(
        "div",
        { ref: this.elRef, className: classNames.join(" "), style: {
          width: props.clientWidth,
          minWidth: props.tableMinWidth
        } },
        y(
          "table",
          { role: "presentation", className: "fc-scrollgrid-sync-table", style: {
            width: props.clientWidth,
            minWidth: props.tableMinWidth,
            height: expandRows ? props.clientHeight : ""
          } },
          props.colGroupNode,
          y(
            "tbody",
            { role: "presentation" },
            y(TableRows, { dateProfile: props.dateProfile, cells: props.cells, renderRowIntro: props.renderRowIntro, showWeekNumbers: props.showWeekNumbers, clientWidth: props.clientWidth, clientHeight: props.clientHeight, businessHourSegs: props.businessHourSegs, bgEventSegs: props.bgEventSegs, fgEventSegs: props.fgEventSegs, dateSelectionSegs: props.dateSelectionSegs, eventSelection: props.eventSelection, eventDrag: props.eventDrag, eventResize: props.eventResize, dayMaxEvents, dayMaxEventRows, forPrint: props.forPrint, isHitComboAllowed: props.isHitComboAllowed })
          )
        )
      );
    }
    componentDidMount() {
      this.requestScrollReset();
    }
    componentDidUpdate(prevProps) {
      if (prevProps.dateProfile !== this.props.dateProfile) {
        this.requestScrollReset();
      } else {
        this.flushScrollReset();
      }
    }
    requestScrollReset() {
      this.needsScrollReset = true;
      this.flushScrollReset();
    }
    flushScrollReset() {
      if (this.needsScrollReset && this.props.clientWidth) {
        const subjectEl = getScrollSubjectEl(this.elRef.current, this.props.dateProfile);
        if (subjectEl) {
          const originEl = subjectEl.closest(".fc-daygrid-body");
          const scrollEl = originEl.closest(".fc-scroller");
          const scrollTop = subjectEl.getBoundingClientRect().top - originEl.getBoundingClientRect().top;
          scrollEl.scrollTop = scrollTop ? scrollTop + 1 : 0;
        }
        this.needsScrollReset = false;
      }
    }
  };
  function getScrollSubjectEl(containerEl, dateProfile) {
    let el;
    if (dateProfile.currentRangeUnit.match(/year|month/)) {
      el = containerEl.querySelector(`[data-date="${formatIsoMonthStr(dateProfile.currentDate)}-01"]`);
    }
    if (!el) {
      el = containerEl.querySelector(`[data-date="${formatDayString(dateProfile.currentDate)}"]`);
    }
    return el;
  }
  var DayTableSlicer = class extends Slicer {
    constructor() {
      super(...arguments);
      this.forceDayIfListItem = true;
    }
    sliceRange(dateRange, dayTableModel) {
      return dayTableModel.sliceRange(dateRange);
    }
  };
  var DayTable = class extends DateComponent {
    constructor() {
      super(...arguments);
      this.slicer = new DayTableSlicer();
      this.tableRef = d();
    }
    render() {
      let { props, context } = this;
      return y(Table, Object.assign({ ref: this.tableRef }, this.slicer.sliceProps(props, props.dateProfile, props.nextDayThreshold, context, props.dayTableModel), { dateProfile: props.dateProfile, cells: props.dayTableModel.cells, colGroupNode: props.colGroupNode, tableMinWidth: props.tableMinWidth, renderRowIntro: props.renderRowIntro, dayMaxEvents: props.dayMaxEvents, dayMaxEventRows: props.dayMaxEventRows, showWeekNumbers: props.showWeekNumbers, expandRows: props.expandRows, headerAlignElRef: props.headerAlignElRef, clientWidth: props.clientWidth, clientHeight: props.clientHeight, forPrint: props.forPrint }));
    }
  };
  var DayTableView = class extends TableView {
    constructor() {
      super(...arguments);
      this.buildDayTableModel = memoize(buildDayTableModel);
      this.headerRef = d();
      this.tableRef = d();
    }
    render() {
      let { options, dateProfileGenerator } = this.context;
      let { props } = this;
      let dayTableModel = this.buildDayTableModel(props.dateProfile, dateProfileGenerator);
      let headerContent = options.dayHeaders && y(DayHeader, { ref: this.headerRef, dateProfile: props.dateProfile, dates: dayTableModel.headerDates, datesRepDistinctDays: dayTableModel.rowCnt === 1 });
      let bodyContent = (contentArg) => y(DayTable, { ref: this.tableRef, dateProfile: props.dateProfile, dayTableModel, businessHours: props.businessHours, dateSelection: props.dateSelection, eventStore: props.eventStore, eventUiBases: props.eventUiBases, eventSelection: props.eventSelection, eventDrag: props.eventDrag, eventResize: props.eventResize, nextDayThreshold: options.nextDayThreshold, colGroupNode: contentArg.tableColGroupNode, tableMinWidth: contentArg.tableMinWidth, dayMaxEvents: options.dayMaxEvents, dayMaxEventRows: options.dayMaxEventRows, showWeekNumbers: options.weekNumbers, expandRows: !props.isHeightAuto, headerAlignElRef: this.headerElRef, clientWidth: contentArg.clientWidth, clientHeight: contentArg.clientHeight, forPrint: props.forPrint });
      return options.dayMinWidth ? this.renderHScrollLayout(headerContent, bodyContent, dayTableModel.colCnt, options.dayMinWidth) : this.renderSimpleLayout(headerContent, bodyContent);
    }
  };
  function buildDayTableModel(dateProfile, dateProfileGenerator) {
    let daySeries = new DaySeriesModel(dateProfile.renderRange, dateProfileGenerator);
    return new DayTableModel(daySeries, /year|month|week/.test(dateProfile.currentRangeUnit));
  }
  var TableDateProfileGenerator = class extends DateProfileGenerator {
    buildRenderRange(currentRange, currentRangeUnit, isRangeAllDay) {
      let renderRange = super.buildRenderRange(currentRange, currentRangeUnit, isRangeAllDay);
      let { props } = this;
      return buildDayTableRenderRange({
        currentRange: renderRange,
        snapToWeek: /^(year|month)$/.test(currentRangeUnit),
        fixedWeekCount: props.fixedWeekCount,
        dateEnv: props.dateEnv
      });
    }
  };
  function buildDayTableRenderRange(props) {
    let { dateEnv, currentRange } = props;
    let { start, end } = currentRange;
    let endOfWeek;
    if (props.snapToWeek) {
      start = dateEnv.startOfWeek(start);
      endOfWeek = dateEnv.startOfWeek(end);
      if (endOfWeek.valueOf() !== end.valueOf()) {
        end = addWeeks(endOfWeek, 1);
      }
    }
    if (props.fixedWeekCount) {
      let lastMonthRenderStart = dateEnv.startOfWeek(dateEnv.startOfMonth(addDays(currentRange.end, -1)));
      let rowCnt = Math.ceil(
        diffWeeks(lastMonthRenderStart, end)
      );
      end = addWeeks(end, 6 - rowCnt);
    }
    return { start, end };
  }
  var css_248z2 = ':root{--fc-daygrid-event-dot-width:8px}.fc-daygrid-day-events:after,.fc-daygrid-day-events:before,.fc-daygrid-day-frame:after,.fc-daygrid-day-frame:before,.fc-daygrid-event-harness:after,.fc-daygrid-event-harness:before{clear:both;content:"";display:table}.fc .fc-daygrid-body{position:relative;z-index:1}.fc .fc-daygrid-day.fc-day-today{background-color:var(--fc-today-bg-color)}.fc .fc-daygrid-day-frame{min-height:100%;position:relative}.fc .fc-daygrid-day-top{display:flex;flex-direction:row-reverse}.fc .fc-day-other .fc-daygrid-day-top{opacity:.3}.fc .fc-daygrid-day-number{padding:4px;position:relative;z-index:4}.fc .fc-daygrid-month-start{font-size:1.1em;font-weight:700}.fc .fc-daygrid-day-events{margin-top:1px}.fc .fc-daygrid-body-balanced .fc-daygrid-day-events{left:0;position:absolute;right:0}.fc .fc-daygrid-body-unbalanced .fc-daygrid-day-events{min-height:2em;position:relative}.fc .fc-daygrid-body-natural .fc-daygrid-day-events{margin-bottom:1em}.fc .fc-daygrid-event-harness{position:relative}.fc .fc-daygrid-event-harness-abs{left:0;position:absolute;right:0;top:0}.fc .fc-daygrid-bg-harness{bottom:0;position:absolute;top:0}.fc .fc-daygrid-day-bg .fc-non-business{z-index:1}.fc .fc-daygrid-day-bg .fc-bg-event{z-index:2}.fc .fc-daygrid-day-bg .fc-highlight{z-index:3}.fc .fc-daygrid-event{margin-top:1px;z-index:6}.fc .fc-daygrid-event.fc-event-mirror{z-index:7}.fc .fc-daygrid-day-bottom{font-size:.85em;margin:0 2px}.fc .fc-daygrid-day-bottom:after,.fc .fc-daygrid-day-bottom:before{clear:both;content:"";display:table}.fc .fc-daygrid-more-link{border-radius:3px;cursor:pointer;line-height:1;margin-top:1px;max-width:100%;overflow:hidden;padding:2px;position:relative;white-space:nowrap;z-index:4}.fc .fc-daygrid-more-link:hover{background-color:rgba(0,0,0,.1)}.fc .fc-daygrid-week-number{background-color:var(--fc-neutral-bg-color);color:var(--fc-neutral-text-color);min-width:1.5em;padding:2px;position:absolute;text-align:center;top:0;z-index:5}.fc .fc-more-popover .fc-popover-body{min-width:220px;padding:10px}.fc-direction-ltr .fc-daygrid-event.fc-event-start,.fc-direction-rtl .fc-daygrid-event.fc-event-end{margin-left:2px}.fc-direction-ltr .fc-daygrid-event.fc-event-end,.fc-direction-rtl .fc-daygrid-event.fc-event-start{margin-right:2px}.fc-direction-ltr .fc-daygrid-more-link{float:left}.fc-direction-ltr .fc-daygrid-week-number{border-radius:0 0 3px 0;left:0}.fc-direction-rtl .fc-daygrid-more-link{float:right}.fc-direction-rtl .fc-daygrid-week-number{border-radius:0 0 0 3px;right:0}.fc-liquid-hack .fc-daygrid-day-frame{position:static}.fc-daygrid-event{border-radius:3px;font-size:var(--fc-small-font-size);position:relative;white-space:nowrap}.fc-daygrid-block-event .fc-event-time{font-weight:700}.fc-daygrid-block-event .fc-event-time,.fc-daygrid-block-event .fc-event-title{padding:1px}.fc-daygrid-dot-event{align-items:center;display:flex;padding:2px 0}.fc-daygrid-dot-event .fc-event-title{flex-grow:1;flex-shrink:1;font-weight:700;min-width:0;overflow:hidden}.fc-daygrid-dot-event.fc-event-mirror,.fc-daygrid-dot-event:hover{background:rgba(0,0,0,.1)}.fc-daygrid-dot-event.fc-event-selected:before{bottom:-10px;top:-10px}.fc-daygrid-event-dot{border:calc(var(--fc-daygrid-event-dot-width)/2) solid var(--fc-event-border-color);border-radius:calc(var(--fc-daygrid-event-dot-width)/2);box-sizing:content-box;height:0;margin:0 4px;width:0}.fc-direction-ltr .fc-daygrid-event .fc-event-time{margin-right:3px}.fc-direction-rtl .fc-daygrid-event .fc-event-time{margin-left:3px}';
  injectStyles(css_248z2);

  // ../ifitwala_ed/node_modules/@fullcalendar/daygrid/index.js
  var index = createPlugin({
    name: "@fullcalendar/daygrid",
    initialView: "dayGridMonth",
    views: {
      dayGrid: {
        component: DayTableView,
        dateProfileGeneratorClass: TableDateProfileGenerator
      },
      dayGridDay: {
        type: "dayGrid",
        duration: { days: 1 }
      },
      dayGridWeek: {
        type: "dayGrid",
        duration: { weeks: 1 }
      },
      dayGridMonth: {
        type: "dayGrid",
        duration: { months: 1 },
        fixedWeekCount: true
      },
      dayGridYear: {
        type: "dayGrid",
        duration: { years: 1 }
      }
    }
  });

  // ../ifitwala_ed/node_modules/@fullcalendar/timegrid/internal.js
  var AllDaySplitter = class extends Splitter {
    getKeyInfo() {
      return {
        allDay: {},
        timed: {}
      };
    }
    getKeysForDateSpan(dateSpan) {
      if (dateSpan.allDay) {
        return ["allDay"];
      }
      return ["timed"];
    }
    getKeysForEventDef(eventDef) {
      if (!eventDef.allDay) {
        return ["timed"];
      }
      if (hasBgRendering(eventDef)) {
        return ["timed", "allDay"];
      }
      return ["allDay"];
    }
  };
  var DEFAULT_SLAT_LABEL_FORMAT = createFormatter({
    hour: "numeric",
    minute: "2-digit",
    omitZeroMinute: true,
    meridiem: "short"
  });
  function TimeColsAxisCell(props) {
    let classNames = [
      "fc-timegrid-slot",
      "fc-timegrid-slot-label",
      props.isLabeled ? "fc-scrollgrid-shrink" : "fc-timegrid-slot-minor"
    ];
    return y(ViewContextType.Consumer, null, (context) => {
      if (!props.isLabeled) {
        return y("td", { className: classNames.join(" "), "data-time": props.isoTimeStr });
      }
      let { dateEnv, options, viewApi } = context;
      let labelFormat = options.slotLabelFormat == null ? DEFAULT_SLAT_LABEL_FORMAT : Array.isArray(options.slotLabelFormat) ? createFormatter(options.slotLabelFormat[0]) : createFormatter(options.slotLabelFormat);
      let renderProps = {
        level: 0,
        time: props.time,
        date: dateEnv.toDate(props.date),
        view: viewApi,
        text: dateEnv.format(props.date, labelFormat)
      };
      return y(ContentContainer, { elTag: "td", elClasses: classNames, elAttrs: {
        "data-time": props.isoTimeStr
      }, renderProps, generatorName: "slotLabelContent", customGenerator: options.slotLabelContent, defaultGenerator: renderInnerContent3, classNameGenerator: options.slotLabelClassNames, didMount: options.slotLabelDidMount, willUnmount: options.slotLabelWillUnmount }, (InnerContent) => y(
        "div",
        { className: "fc-timegrid-slot-label-frame fc-scrollgrid-shrink-frame" },
        y(InnerContent, { elTag: "div", elClasses: [
          "fc-timegrid-slot-label-cushion",
          "fc-scrollgrid-shrink-cushion"
        ] })
      ));
    });
  }
  function renderInnerContent3(props) {
    return props.text;
  }
  var TimeBodyAxis = class extends BaseComponent {
    render() {
      return this.props.slatMetas.map((slatMeta) => y(
        "tr",
        { key: slatMeta.key },
        y(TimeColsAxisCell, Object.assign({}, slatMeta))
      ));
    }
  };
  var DEFAULT_WEEK_NUM_FORMAT2 = createFormatter({ week: "short" });
  var AUTO_ALL_DAY_MAX_EVENT_ROWS = 5;
  var TimeColsView = class extends DateComponent {
    constructor() {
      super(...arguments);
      this.allDaySplitter = new AllDaySplitter();
      this.headerElRef = d();
      this.rootElRef = d();
      this.scrollerElRef = d();
      this.state = {
        slatCoords: null
      };
      this.handleScrollTopRequest = (scrollTop) => {
        let scrollerEl = this.scrollerElRef.current;
        if (scrollerEl) {
          scrollerEl.scrollTop = scrollTop;
        }
      };
      this.renderHeadAxis = (rowKey, frameHeight = "") => {
        let { options } = this.context;
        let { dateProfile } = this.props;
        let range = dateProfile.renderRange;
        let dayCnt = diffDays(range.start, range.end);
        let navLinkAttrs = dayCnt === 1 ? buildNavLinkAttrs(this.context, range.start, "week") : {};
        if (options.weekNumbers && rowKey === "day") {
          return y(WeekNumberContainer, { elTag: "th", elClasses: [
            "fc-timegrid-axis",
            "fc-scrollgrid-shrink"
          ], elAttrs: {
            "aria-hidden": true
          }, date: range.start, defaultFormat: DEFAULT_WEEK_NUM_FORMAT2 }, (InnerContent) => y(
            "div",
            { className: [
              "fc-timegrid-axis-frame",
              "fc-scrollgrid-shrink-frame",
              "fc-timegrid-axis-frame-liquid"
            ].join(" "), style: { height: frameHeight } },
            y(InnerContent, { elTag: "a", elClasses: [
              "fc-timegrid-axis-cushion",
              "fc-scrollgrid-shrink-cushion",
              "fc-scrollgrid-sync-inner"
            ], elAttrs: navLinkAttrs })
          ));
        }
        return y(
          "th",
          { "aria-hidden": true, className: "fc-timegrid-axis" },
          y("div", { className: "fc-timegrid-axis-frame", style: { height: frameHeight } })
        );
      };
      this.renderTableRowAxis = (rowHeight) => {
        let { options, viewApi } = this.context;
        let renderProps = {
          text: options.allDayText,
          view: viewApi
        };
        return y(ContentContainer, { elTag: "td", elClasses: [
          "fc-timegrid-axis",
          "fc-scrollgrid-shrink"
        ], elAttrs: {
          "aria-hidden": true
        }, renderProps, generatorName: "allDayContent", customGenerator: options.allDayContent, defaultGenerator: renderAllDayInner, classNameGenerator: options.allDayClassNames, didMount: options.allDayDidMount, willUnmount: options.allDayWillUnmount }, (InnerContent) => y(
          "div",
          { className: [
            "fc-timegrid-axis-frame",
            "fc-scrollgrid-shrink-frame",
            rowHeight == null ? " fc-timegrid-axis-frame-liquid" : ""
          ].join(" "), style: { height: rowHeight } },
          y(InnerContent, { elTag: "span", elClasses: [
            "fc-timegrid-axis-cushion",
            "fc-scrollgrid-shrink-cushion",
            "fc-scrollgrid-sync-inner"
          ] })
        ));
      };
      this.handleSlatCoords = (slatCoords) => {
        this.setState({ slatCoords });
      };
    }
    renderSimpleLayout(headerRowContent, allDayContent, timeContent) {
      let { context, props } = this;
      let sections = [];
      let stickyHeaderDates = getStickyHeaderDates(context.options);
      if (headerRowContent) {
        sections.push({
          type: "header",
          key: "header",
          isSticky: stickyHeaderDates,
          chunk: {
            elRef: this.headerElRef,
            tableClassName: "fc-col-header",
            rowContent: headerRowContent
          }
        });
      }
      if (allDayContent) {
        sections.push({
          type: "body",
          key: "all-day",
          chunk: { content: allDayContent }
        });
        sections.push({
          type: "body",
          key: "all-day-divider",
          outerContent: y(
            "tr",
            { role: "presentation", className: "fc-scrollgrid-section" },
            y("td", { className: "fc-timegrid-divider " + context.theme.getClass("tableCellShaded") })
          )
        });
      }
      sections.push({
        type: "body",
        key: "body",
        liquid: true,
        expandRows: Boolean(context.options.expandRows),
        chunk: {
          scrollerElRef: this.scrollerElRef,
          content: timeContent
        }
      });
      return y(
        ViewContainer,
        { elRef: this.rootElRef, elClasses: ["fc-timegrid"], viewSpec: context.viewSpec },
        y(SimpleScrollGrid, { liquid: !props.isHeightAuto && !props.forPrint, collapsibleWidth: props.forPrint, cols: [{ width: "shrink" }], sections })
      );
    }
    renderHScrollLayout(headerRowContent, allDayContent, timeContent, colCnt, dayMinWidth, slatMetas, slatCoords) {
      let ScrollGrid = this.context.pluginHooks.scrollGridImpl;
      if (!ScrollGrid) {
        throw new Error("No ScrollGrid implementation");
      }
      let { context, props } = this;
      let stickyHeaderDates = !props.forPrint && getStickyHeaderDates(context.options);
      let stickyFooterScrollbar = !props.forPrint && getStickyFooterScrollbar(context.options);
      let sections = [];
      if (headerRowContent) {
        sections.push({
          type: "header",
          key: "header",
          isSticky: stickyHeaderDates,
          syncRowHeights: true,
          chunks: [
            {
              key: "axis",
              rowContent: (arg) => y("tr", { role: "presentation" }, this.renderHeadAxis("day", arg.rowSyncHeights[0]))
            },
            {
              key: "cols",
              elRef: this.headerElRef,
              tableClassName: "fc-col-header",
              rowContent: headerRowContent
            }
          ]
        });
      }
      if (allDayContent) {
        sections.push({
          type: "body",
          key: "all-day",
          syncRowHeights: true,
          chunks: [
            {
              key: "axis",
              rowContent: (contentArg) => y("tr", { role: "presentation" }, this.renderTableRowAxis(contentArg.rowSyncHeights[0]))
            },
            {
              key: "cols",
              content: allDayContent
            }
          ]
        });
        sections.push({
          key: "all-day-divider",
          type: "body",
          outerContent: y(
            "tr",
            { role: "presentation", className: "fc-scrollgrid-section" },
            y("td", { colSpan: 2, className: "fc-timegrid-divider " + context.theme.getClass("tableCellShaded") })
          )
        });
      }
      let isNowIndicator = context.options.nowIndicator;
      sections.push({
        type: "body",
        key: "body",
        liquid: true,
        expandRows: Boolean(context.options.expandRows),
        chunks: [
          {
            key: "axis",
            content: (arg) => y(
              "div",
              { className: "fc-timegrid-axis-chunk" },
              y(
                "table",
                { "aria-hidden": true, style: { height: arg.expandRows ? arg.clientHeight : "" } },
                arg.tableColGroupNode,
                y(
                  "tbody",
                  null,
                  y(TimeBodyAxis, { slatMetas })
                )
              ),
              y(
                "div",
                { className: "fc-timegrid-now-indicator-container" },
                y(NowTimer, { unit: isNowIndicator ? "minute" : "day" }, (nowDate) => {
                  let nowIndicatorTop = isNowIndicator && slatCoords && slatCoords.safeComputeTop(nowDate);
                  if (typeof nowIndicatorTop === "number") {
                    return y(NowIndicatorContainer, { elClasses: ["fc-timegrid-now-indicator-arrow"], elStyle: { top: nowIndicatorTop }, isAxis: true, date: nowDate });
                  }
                  return null;
                })
              )
            )
          },
          {
            key: "cols",
            scrollerElRef: this.scrollerElRef,
            content: timeContent
          }
        ]
      });
      if (stickyFooterScrollbar) {
        sections.push({
          key: "footer",
          type: "footer",
          isSticky: true,
          chunks: [
            {
              key: "axis",
              content: renderScrollShim
            },
            {
              key: "cols",
              content: renderScrollShim
            }
          ]
        });
      }
      return y(
        ViewContainer,
        { elRef: this.rootElRef, elClasses: ["fc-timegrid"], viewSpec: context.viewSpec },
        y(ScrollGrid, { liquid: !props.isHeightAuto && !props.forPrint, forPrint: props.forPrint, collapsibleWidth: false, colGroups: [
          { width: "shrink", cols: [{ width: "shrink" }] },
          { cols: [{ span: colCnt, minWidth: dayMinWidth }] }
        ], sections })
      );
    }
    getAllDayMaxEventProps() {
      let { dayMaxEvents, dayMaxEventRows } = this.context.options;
      if (dayMaxEvents === true || dayMaxEventRows === true) {
        dayMaxEvents = void 0;
        dayMaxEventRows = AUTO_ALL_DAY_MAX_EVENT_ROWS;
      }
      return { dayMaxEvents, dayMaxEventRows };
    }
  };
  function renderAllDayInner(renderProps) {
    return renderProps.text;
  }
  var TimeColsSlatsCoords = class {
    constructor(positions, dateProfile, slotDuration) {
      this.positions = positions;
      this.dateProfile = dateProfile;
      this.slotDuration = slotDuration;
    }
    safeComputeTop(date) {
      let { dateProfile } = this;
      if (rangeContainsMarker(dateProfile.currentRange, date)) {
        let startOfDayDate = startOfDay(date);
        let timeMs = date.valueOf() - startOfDayDate.valueOf();
        if (timeMs >= asRoughMs(dateProfile.slotMinTime) && timeMs < asRoughMs(dateProfile.slotMaxTime)) {
          return this.computeTimeTop(createDuration(timeMs));
        }
      }
      return null;
    }
    computeDateTop(when, startOfDayDate) {
      if (!startOfDayDate) {
        startOfDayDate = startOfDay(when);
      }
      return this.computeTimeTop(createDuration(when.valueOf() - startOfDayDate.valueOf()));
    }
    computeTimeTop(duration) {
      let { positions, dateProfile } = this;
      let len = positions.els.length;
      let slatCoverage = (duration.milliseconds - asRoughMs(dateProfile.slotMinTime)) / asRoughMs(this.slotDuration);
      let slatIndex;
      let slatRemainder;
      slatCoverage = Math.max(0, slatCoverage);
      slatCoverage = Math.min(len, slatCoverage);
      slatIndex = Math.floor(slatCoverage);
      slatIndex = Math.min(slatIndex, len - 1);
      slatRemainder = slatCoverage - slatIndex;
      return positions.tops[slatIndex] + positions.getHeight(slatIndex) * slatRemainder;
    }
  };
  var TimeColsSlatsBody = class extends BaseComponent {
    render() {
      let { props, context } = this;
      let { options } = context;
      let { slatElRefs } = props;
      return y("tbody", null, props.slatMetas.map((slatMeta, i3) => {
        let renderProps = {
          time: slatMeta.time,
          date: context.dateEnv.toDate(slatMeta.date),
          view: context.viewApi
        };
        return y(
          "tr",
          { key: slatMeta.key, ref: slatElRefs.createRef(slatMeta.key) },
          props.axis && y(TimeColsAxisCell, Object.assign({}, slatMeta)),
          y(ContentContainer, { elTag: "td", elClasses: [
            "fc-timegrid-slot",
            "fc-timegrid-slot-lane",
            !slatMeta.isLabeled && "fc-timegrid-slot-minor"
          ], elAttrs: {
            "data-time": slatMeta.isoTimeStr
          }, renderProps, generatorName: "slotLaneContent", customGenerator: options.slotLaneContent, classNameGenerator: options.slotLaneClassNames, didMount: options.slotLaneDidMount, willUnmount: options.slotLaneWillUnmount })
        );
      }));
    }
  };
  var TimeColsSlats = class extends BaseComponent {
    constructor() {
      super(...arguments);
      this.rootElRef = d();
      this.slatElRefs = new RefMap();
    }
    render() {
      let { props, context } = this;
      return y(
        "div",
        { ref: this.rootElRef, className: "fc-timegrid-slots" },
        y(
          "table",
          { "aria-hidden": true, className: context.theme.getClass("table"), style: {
            minWidth: props.tableMinWidth,
            width: props.clientWidth,
            height: props.minHeight
          } },
          props.tableColGroupNode,
          y(TimeColsSlatsBody, { slatElRefs: this.slatElRefs, axis: props.axis, slatMetas: props.slatMetas })
        )
      );
    }
    componentDidMount() {
      this.updateSizing();
    }
    componentDidUpdate() {
      this.updateSizing();
    }
    componentWillUnmount() {
      if (this.props.onCoords) {
        this.props.onCoords(null);
      }
    }
    updateSizing() {
      let { context, props } = this;
      if (props.onCoords && props.clientWidth !== null) {
        let rootEl = this.rootElRef.current;
        if (rootEl.offsetHeight) {
          props.onCoords(new TimeColsSlatsCoords(new PositionCache(this.rootElRef.current, collectSlatEls(this.slatElRefs.currentMap, props.slatMetas), false, true), this.props.dateProfile, context.options.slotDuration));
        }
      }
    }
  };
  function collectSlatEls(elMap, slatMetas) {
    return slatMetas.map((slatMeta) => elMap[slatMeta.key]);
  }
  function splitSegsByCol(segs, colCnt) {
    let segsByCol = [];
    let i3;
    for (i3 = 0; i3 < colCnt; i3 += 1) {
      segsByCol.push([]);
    }
    if (segs) {
      for (i3 = 0; i3 < segs.length; i3 += 1) {
        segsByCol[segs[i3].col].push(segs[i3]);
      }
    }
    return segsByCol;
  }
  function splitInteractionByCol(ui, colCnt) {
    let byRow = [];
    if (!ui) {
      for (let i3 = 0; i3 < colCnt; i3 += 1) {
        byRow[i3] = null;
      }
    } else {
      for (let i3 = 0; i3 < colCnt; i3 += 1) {
        byRow[i3] = {
          affectedInstances: ui.affectedInstances,
          isEvent: ui.isEvent,
          segs: []
        };
      }
      for (let seg of ui.segs) {
        byRow[seg.col].segs.push(seg);
      }
    }
    return byRow;
  }
  var TimeColMoreLink = class extends BaseComponent {
    render() {
      let { props } = this;
      return y(MoreLinkContainer, { elClasses: ["fc-timegrid-more-link"], elStyle: {
        top: props.top,
        bottom: props.bottom
      }, allDayDate: null, moreCnt: props.hiddenSegs.length, allSegs: props.hiddenSegs, hiddenSegs: props.hiddenSegs, extraDateSpan: props.extraDateSpan, dateProfile: props.dateProfile, todayRange: props.todayRange, popoverContent: () => renderPlainFgSegs(props.hiddenSegs, props), defaultGenerator: renderMoreLinkInner2, forceTimed: true }, (InnerContent) => y(InnerContent, { elTag: "div", elClasses: ["fc-timegrid-more-link-inner", "fc-sticky"] }));
    }
  };
  function renderMoreLinkInner2(props) {
    return props.shortText;
  }
  function buildPositioning(segInputs, strictOrder, maxStackCnt) {
    let hierarchy = new SegHierarchy();
    if (strictOrder != null) {
      hierarchy.strictOrder = strictOrder;
    }
    if (maxStackCnt != null) {
      hierarchy.maxStackCnt = maxStackCnt;
    }
    let hiddenEntries = hierarchy.addSegs(segInputs);
    let hiddenGroups = groupIntersectingEntries(hiddenEntries);
    let web = buildWeb(hierarchy);
    web = stretchWeb(web, 1);
    let segRects = webToRects(web);
    return { segRects, hiddenGroups };
  }
  function buildWeb(hierarchy) {
    const { entriesByLevel } = hierarchy;
    const buildNode = cacheable((level, lateral) => level + ":" + lateral, (level, lateral) => {
      let siblingRange = findNextLevelSegs(hierarchy, level, lateral);
      let nextLevelRes = buildNodes(siblingRange, buildNode);
      let entry = entriesByLevel[level][lateral];
      return [
        Object.assign(Object.assign({}, entry), { nextLevelNodes: nextLevelRes[0] }),
        entry.thickness + nextLevelRes[1]
      ];
    });
    return buildNodes(entriesByLevel.length ? { level: 0, lateralStart: 0, lateralEnd: entriesByLevel[0].length } : null, buildNode)[0];
  }
  function buildNodes(siblingRange, buildNode) {
    if (!siblingRange) {
      return [[], 0];
    }
    let { level, lateralStart, lateralEnd } = siblingRange;
    let lateral = lateralStart;
    let pairs = [];
    while (lateral < lateralEnd) {
      pairs.push(buildNode(level, lateral));
      lateral += 1;
    }
    pairs.sort(cmpDescPressures);
    return [
      pairs.map(extractNode),
      pairs[0][1]
    ];
  }
  function cmpDescPressures(a3, b3) {
    return b3[1] - a3[1];
  }
  function extractNode(a3) {
    return a3[0];
  }
  function findNextLevelSegs(hierarchy, subjectLevel, subjectLateral) {
    let { levelCoords, entriesByLevel } = hierarchy;
    let subjectEntry = entriesByLevel[subjectLevel][subjectLateral];
    let afterSubject = levelCoords[subjectLevel] + subjectEntry.thickness;
    let levelCnt = levelCoords.length;
    let level = subjectLevel;
    for (; level < levelCnt && levelCoords[level] < afterSubject; level += 1)
      ;
    for (; level < levelCnt; level += 1) {
      let entries = entriesByLevel[level];
      let entry;
      let searchIndex = binarySearch(entries, subjectEntry.span.start, getEntrySpanEnd);
      let lateralStart = searchIndex[0] + searchIndex[1];
      let lateralEnd = lateralStart;
      while ((entry = entries[lateralEnd]) && entry.span.start < subjectEntry.span.end) {
        lateralEnd += 1;
      }
      if (lateralStart < lateralEnd) {
        return { level, lateralStart, lateralEnd };
      }
    }
    return null;
  }
  function stretchWeb(topLevelNodes, totalThickness) {
    const stretchNode = cacheable((node, startCoord, prevThickness) => buildEntryKey(node), (node, startCoord, prevThickness) => {
      let { nextLevelNodes, thickness } = node;
      let allThickness = thickness + prevThickness;
      let thicknessFraction = thickness / allThickness;
      let endCoord;
      let newChildren = [];
      if (!nextLevelNodes.length) {
        endCoord = totalThickness;
      } else {
        for (let childNode of nextLevelNodes) {
          if (endCoord === void 0) {
            let res = stretchNode(childNode, startCoord, allThickness);
            endCoord = res[0];
            newChildren.push(res[1]);
          } else {
            let res = stretchNode(childNode, endCoord, 0);
            newChildren.push(res[1]);
          }
        }
      }
      let newThickness = (endCoord - startCoord) * thicknessFraction;
      return [endCoord - newThickness, Object.assign(Object.assign({}, node), { thickness: newThickness, nextLevelNodes: newChildren })];
    });
    return topLevelNodes.map((node) => stretchNode(node, 0, 0)[1]);
  }
  function webToRects(topLevelNodes) {
    let rects = [];
    const processNode = cacheable((node, levelCoord, stackDepth) => buildEntryKey(node), (node, levelCoord, stackDepth) => {
      let rect = Object.assign(Object.assign({}, node), {
        levelCoord,
        stackDepth,
        stackForward: 0
      });
      rects.push(rect);
      return rect.stackForward = processNodes(node.nextLevelNodes, levelCoord + node.thickness, stackDepth + 1) + 1;
    });
    function processNodes(nodes, levelCoord, stackDepth) {
      let stackForward = 0;
      for (let node of nodes) {
        stackForward = Math.max(processNode(node, levelCoord, stackDepth), stackForward);
      }
      return stackForward;
    }
    processNodes(topLevelNodes, 0, 0);
    return rects;
  }
  function cacheable(keyFunc, workFunc) {
    const cache = {};
    return (...args) => {
      let key = keyFunc(...args);
      return key in cache ? cache[key] : cache[key] = workFunc(...args);
    };
  }
  function computeSegVCoords(segs, colDate, slatCoords = null, eventMinHeight = 0) {
    let vcoords = [];
    if (slatCoords) {
      for (let i3 = 0; i3 < segs.length; i3 += 1) {
        let seg = segs[i3];
        let spanStart = slatCoords.computeDateTop(seg.start, colDate);
        let spanEnd = Math.max(
          spanStart + (eventMinHeight || 0),
          slatCoords.computeDateTop(seg.end, colDate)
        );
        vcoords.push({
          start: Math.round(spanStart),
          end: Math.round(spanEnd)
        });
      }
    }
    return vcoords;
  }
  function computeFgSegPlacements(segs, segVCoords, eventOrderStrict, eventMaxStack) {
    let segInputs = [];
    let dumbSegs = [];
    for (let i3 = 0; i3 < segs.length; i3 += 1) {
      let vcoords = segVCoords[i3];
      if (vcoords) {
        segInputs.push({
          index: i3,
          thickness: 1,
          span: vcoords
        });
      } else {
        dumbSegs.push(segs[i3]);
      }
    }
    let { segRects, hiddenGroups } = buildPositioning(segInputs, eventOrderStrict, eventMaxStack);
    let segPlacements = [];
    for (let segRect of segRects) {
      segPlacements.push({
        seg: segs[segRect.index],
        rect: segRect
      });
    }
    for (let dumbSeg of dumbSegs) {
      segPlacements.push({ seg: dumbSeg, rect: null });
    }
    return { segPlacements, hiddenGroups };
  }
  var DEFAULT_TIME_FORMAT = createFormatter({
    hour: "numeric",
    minute: "2-digit",
    meridiem: false
  });
  var TimeColEvent = class extends BaseComponent {
    render() {
      return y(StandardEvent, Object.assign({}, this.props, { elClasses: [
        "fc-timegrid-event",
        "fc-v-event",
        this.props.isShort && "fc-timegrid-event-short"
      ], defaultTimeFormat: DEFAULT_TIME_FORMAT }));
    }
  };
  var TimeCol = class extends BaseComponent {
    constructor() {
      super(...arguments);
      this.sortEventSegs = memoize(sortEventSegs);
    }
    render() {
      let { props, context } = this;
      let { options } = context;
      let isSelectMirror = options.selectMirror;
      let mirrorSegs = props.eventDrag && props.eventDrag.segs || props.eventResize && props.eventResize.segs || isSelectMirror && props.dateSelectionSegs || [];
      let interactionAffectedInstances = props.eventDrag && props.eventDrag.affectedInstances || props.eventResize && props.eventResize.affectedInstances || {};
      let sortedFgSegs = this.sortEventSegs(props.fgEventSegs, options.eventOrder);
      return y(DayCellContainer, { elTag: "td", elRef: props.elRef, elClasses: [
        "fc-timegrid-col",
        ...props.extraClassNames || []
      ], elAttrs: Object.assign({ role: "gridcell" }, props.extraDataAttrs), date: props.date, dateProfile: props.dateProfile, todayRange: props.todayRange, extraRenderProps: props.extraRenderProps }, (InnerContent) => y(
        "div",
        { className: "fc-timegrid-col-frame" },
        y(
          "div",
          { className: "fc-timegrid-col-bg" },
          this.renderFillSegs(props.businessHourSegs, "non-business"),
          this.renderFillSegs(props.bgEventSegs, "bg-event"),
          this.renderFillSegs(props.dateSelectionSegs, "highlight")
        ),
        y("div", { className: "fc-timegrid-col-events" }, this.renderFgSegs(sortedFgSegs, interactionAffectedInstances, false, false, false)),
        y("div", { className: "fc-timegrid-col-events" }, this.renderFgSegs(mirrorSegs, {}, Boolean(props.eventDrag), Boolean(props.eventResize), Boolean(isSelectMirror), "mirror")),
        y("div", { className: "fc-timegrid-now-indicator-container" }, this.renderNowIndicator(props.nowIndicatorSegs)),
        hasCustomDayCellContent(options) && y(InnerContent, { elTag: "div", elClasses: ["fc-timegrid-col-misc"] })
      ));
    }
    renderFgSegs(sortedFgSegs, segIsInvisible, isDragging, isResizing, isDateSelecting, forcedKey) {
      let { props } = this;
      if (props.forPrint) {
        return renderPlainFgSegs(sortedFgSegs, props);
      }
      return this.renderPositionedFgSegs(sortedFgSegs, segIsInvisible, isDragging, isResizing, isDateSelecting, forcedKey);
    }
    renderPositionedFgSegs(segs, segIsInvisible, isDragging, isResizing, isDateSelecting, forcedKey) {
      let { eventMaxStack, eventShortHeight, eventOrderStrict, eventMinHeight } = this.context.options;
      let { date, slatCoords, eventSelection, todayRange, nowDate } = this.props;
      let isMirror = isDragging || isResizing || isDateSelecting;
      let segVCoords = computeSegVCoords(segs, date, slatCoords, eventMinHeight);
      let { segPlacements, hiddenGroups } = computeFgSegPlacements(segs, segVCoords, eventOrderStrict, eventMaxStack);
      return y(
        _,
        null,
        this.renderHiddenGroups(hiddenGroups, segs),
        segPlacements.map((segPlacement) => {
          let { seg, rect } = segPlacement;
          let instanceId = seg.eventRange.instance.instanceId;
          let isVisible = isMirror || Boolean(!segIsInvisible[instanceId] && rect);
          let vStyle = computeSegVStyle(rect && rect.span);
          let hStyle = !isMirror && rect ? this.computeSegHStyle(rect) : { left: 0, right: 0 };
          let isInset = Boolean(rect) && rect.stackForward > 0;
          let isShort = Boolean(rect) && rect.span.end - rect.span.start < eventShortHeight;
          return y(
            "div",
            { className: "fc-timegrid-event-harness" + (isInset ? " fc-timegrid-event-harness-inset" : ""), key: forcedKey || instanceId, style: Object.assign(Object.assign({ visibility: isVisible ? "" : "hidden" }, vStyle), hStyle) },
            y(TimeColEvent, Object.assign({ seg, isDragging, isResizing, isDateSelecting, isSelected: instanceId === eventSelection, isShort }, getSegMeta(seg, todayRange, nowDate)))
          );
        })
      );
    }
    renderHiddenGroups(hiddenGroups, segs) {
      let { extraDateSpan, dateProfile, todayRange, nowDate, eventSelection, eventDrag, eventResize } = this.props;
      return y(_, null, hiddenGroups.map((hiddenGroup) => {
        let positionCss = computeSegVStyle(hiddenGroup.span);
        let hiddenSegs = compileSegsFromEntries(hiddenGroup.entries, segs);
        return y(TimeColMoreLink, { key: buildIsoString(computeEarliestSegStart(hiddenSegs)), hiddenSegs, top: positionCss.top, bottom: positionCss.bottom, extraDateSpan, dateProfile, todayRange, nowDate, eventSelection, eventDrag, eventResize });
      }));
    }
    renderFillSegs(segs, fillType) {
      let { props, context } = this;
      let segVCoords = computeSegVCoords(segs, props.date, props.slatCoords, context.options.eventMinHeight);
      let children = segVCoords.map((vcoords, i3) => {
        let seg = segs[i3];
        return y("div", { key: buildEventRangeKey(seg.eventRange), className: "fc-timegrid-bg-harness", style: computeSegVStyle(vcoords) }, fillType === "bg-event" ? y(BgEvent, Object.assign({ seg }, getSegMeta(seg, props.todayRange, props.nowDate))) : renderFill(fillType));
      });
      return y(_, null, children);
    }
    renderNowIndicator(segs) {
      let { slatCoords, date } = this.props;
      if (!slatCoords) {
        return null;
      }
      return segs.map((seg, i3) => y(
        NowIndicatorContainer,
        {
          key: i3,
          elClasses: ["fc-timegrid-now-indicator-line"],
          elStyle: {
            top: slatCoords.computeDateTop(seg.start, date)
          },
          isAxis: false,
          date
        }
      ));
    }
    computeSegHStyle(segHCoords) {
      let { isRtl, options } = this.context;
      let shouldOverlap = options.slotEventOverlap;
      let nearCoord = segHCoords.levelCoord;
      let farCoord = segHCoords.levelCoord + segHCoords.thickness;
      let left;
      let right;
      if (shouldOverlap) {
        farCoord = Math.min(1, nearCoord + (farCoord - nearCoord) * 2);
      }
      if (isRtl) {
        left = 1 - farCoord;
        right = nearCoord;
      } else {
        left = nearCoord;
        right = 1 - farCoord;
      }
      let props = {
        zIndex: segHCoords.stackDepth + 1,
        left: left * 100 + "%",
        right: right * 100 + "%"
      };
      if (shouldOverlap && !segHCoords.stackForward) {
        props[isRtl ? "marginLeft" : "marginRight"] = 10 * 2;
      }
      return props;
    }
  };
  function renderPlainFgSegs(sortedFgSegs, { todayRange, nowDate, eventSelection, eventDrag, eventResize }) {
    let hiddenInstances = (eventDrag ? eventDrag.affectedInstances : null) || (eventResize ? eventResize.affectedInstances : null) || {};
    return y(_, null, sortedFgSegs.map((seg) => {
      let instanceId = seg.eventRange.instance.instanceId;
      return y(
        "div",
        { key: instanceId, style: { visibility: hiddenInstances[instanceId] ? "hidden" : "" } },
        y(TimeColEvent, Object.assign({ seg, isDragging: false, isResizing: false, isDateSelecting: false, isSelected: instanceId === eventSelection, isShort: false }, getSegMeta(seg, todayRange, nowDate)))
      );
    }));
  }
  function computeSegVStyle(segVCoords) {
    if (!segVCoords) {
      return { top: "", bottom: "" };
    }
    return {
      top: segVCoords.start,
      bottom: -segVCoords.end
    };
  }
  function compileSegsFromEntries(segEntries, allSegs) {
    return segEntries.map((segEntry) => allSegs[segEntry.index]);
  }
  var TimeColsContent = class extends BaseComponent {
    constructor() {
      super(...arguments);
      this.splitFgEventSegs = memoize(splitSegsByCol);
      this.splitBgEventSegs = memoize(splitSegsByCol);
      this.splitBusinessHourSegs = memoize(splitSegsByCol);
      this.splitNowIndicatorSegs = memoize(splitSegsByCol);
      this.splitDateSelectionSegs = memoize(splitSegsByCol);
      this.splitEventDrag = memoize(splitInteractionByCol);
      this.splitEventResize = memoize(splitInteractionByCol);
      this.rootElRef = d();
      this.cellElRefs = new RefMap();
    }
    render() {
      let { props, context } = this;
      let nowIndicatorTop = context.options.nowIndicator && props.slatCoords && props.slatCoords.safeComputeTop(props.nowDate);
      let colCnt = props.cells.length;
      let fgEventSegsByRow = this.splitFgEventSegs(props.fgEventSegs, colCnt);
      let bgEventSegsByRow = this.splitBgEventSegs(props.bgEventSegs, colCnt);
      let businessHourSegsByRow = this.splitBusinessHourSegs(props.businessHourSegs, colCnt);
      let nowIndicatorSegsByRow = this.splitNowIndicatorSegs(props.nowIndicatorSegs, colCnt);
      let dateSelectionSegsByRow = this.splitDateSelectionSegs(props.dateSelectionSegs, colCnt);
      let eventDragByRow = this.splitEventDrag(props.eventDrag, colCnt);
      let eventResizeByRow = this.splitEventResize(props.eventResize, colCnt);
      return y(
        "div",
        { className: "fc-timegrid-cols", ref: this.rootElRef },
        y(
          "table",
          { role: "presentation", style: {
            minWidth: props.tableMinWidth,
            width: props.clientWidth
          } },
          props.tableColGroupNode,
          y(
            "tbody",
            { role: "presentation" },
            y(
              "tr",
              { role: "row" },
              props.axis && y(
                "td",
                { "aria-hidden": true, className: "fc-timegrid-col fc-timegrid-axis" },
                y(
                  "div",
                  { className: "fc-timegrid-col-frame" },
                  y("div", { className: "fc-timegrid-now-indicator-container" }, typeof nowIndicatorTop === "number" && y(NowIndicatorContainer, { elClasses: ["fc-timegrid-now-indicator-arrow"], elStyle: { top: nowIndicatorTop }, isAxis: true, date: props.nowDate }))
                )
              ),
              props.cells.map((cell, i3) => y(TimeCol, { key: cell.key, elRef: this.cellElRefs.createRef(cell.key), dateProfile: props.dateProfile, date: cell.date, nowDate: props.nowDate, todayRange: props.todayRange, extraRenderProps: cell.extraRenderProps, extraDataAttrs: cell.extraDataAttrs, extraClassNames: cell.extraClassNames, extraDateSpan: cell.extraDateSpan, fgEventSegs: fgEventSegsByRow[i3], bgEventSegs: bgEventSegsByRow[i3], businessHourSegs: businessHourSegsByRow[i3], nowIndicatorSegs: nowIndicatorSegsByRow[i3], dateSelectionSegs: dateSelectionSegsByRow[i3], eventDrag: eventDragByRow[i3], eventResize: eventResizeByRow[i3], slatCoords: props.slatCoords, eventSelection: props.eventSelection, forPrint: props.forPrint }))
            )
          )
        )
      );
    }
    componentDidMount() {
      this.updateCoords();
    }
    componentDidUpdate() {
      this.updateCoords();
    }
    updateCoords() {
      let { props } = this;
      if (props.onColCoords && props.clientWidth !== null) {
        props.onColCoords(new PositionCache(
          this.rootElRef.current,
          collectCellEls(this.cellElRefs.currentMap, props.cells),
          true,
          false
        ));
      }
    }
  };
  function collectCellEls(elMap, cells) {
    return cells.map((cell) => elMap[cell.key]);
  }
  var TimeCols = class extends DateComponent {
    constructor() {
      super(...arguments);
      this.processSlotOptions = memoize(processSlotOptions);
      this.state = {
        slatCoords: null
      };
      this.handleRootEl = (el) => {
        if (el) {
          this.context.registerInteractiveComponent(this, {
            el,
            isHitComboAllowed: this.props.isHitComboAllowed
          });
        } else {
          this.context.unregisterInteractiveComponent(this);
        }
      };
      this.handleScrollRequest = (request) => {
        let { onScrollTopRequest } = this.props;
        let { slatCoords } = this.state;
        if (onScrollTopRequest && slatCoords) {
          if (request.time) {
            let top = slatCoords.computeTimeTop(request.time);
            top = Math.ceil(top);
            if (top) {
              top += 1;
            }
            onScrollTopRequest(top);
          }
          return true;
        }
        return false;
      };
      this.handleColCoords = (colCoords) => {
        this.colCoords = colCoords;
      };
      this.handleSlatCoords = (slatCoords) => {
        this.setState({ slatCoords });
        if (this.props.onSlatCoords) {
          this.props.onSlatCoords(slatCoords);
        }
      };
    }
    render() {
      let { props, state } = this;
      return y(
        "div",
        { className: "fc-timegrid-body", ref: this.handleRootEl, style: {
          width: props.clientWidth,
          minWidth: props.tableMinWidth
        } },
        y(TimeColsSlats, { axis: props.axis, dateProfile: props.dateProfile, slatMetas: props.slatMetas, clientWidth: props.clientWidth, minHeight: props.expandRows ? props.clientHeight : "", tableMinWidth: props.tableMinWidth, tableColGroupNode: props.axis ? props.tableColGroupNode : null, onCoords: this.handleSlatCoords }),
        y(TimeColsContent, { cells: props.cells, axis: props.axis, dateProfile: props.dateProfile, businessHourSegs: props.businessHourSegs, bgEventSegs: props.bgEventSegs, fgEventSegs: props.fgEventSegs, dateSelectionSegs: props.dateSelectionSegs, eventSelection: props.eventSelection, eventDrag: props.eventDrag, eventResize: props.eventResize, todayRange: props.todayRange, nowDate: props.nowDate, nowIndicatorSegs: props.nowIndicatorSegs, clientWidth: props.clientWidth, tableMinWidth: props.tableMinWidth, tableColGroupNode: props.tableColGroupNode, slatCoords: state.slatCoords, onColCoords: this.handleColCoords, forPrint: props.forPrint })
      );
    }
    componentDidMount() {
      this.scrollResponder = this.context.createScrollResponder(this.handleScrollRequest);
    }
    componentDidUpdate(prevProps) {
      this.scrollResponder.update(prevProps.dateProfile !== this.props.dateProfile);
    }
    componentWillUnmount() {
      this.scrollResponder.detach();
    }
    queryHit(positionLeft, positionTop) {
      let { dateEnv, options } = this.context;
      let { colCoords } = this;
      let { dateProfile } = this.props;
      let { slatCoords } = this.state;
      let { snapDuration, snapsPerSlot } = this.processSlotOptions(this.props.slotDuration, options.snapDuration);
      let colIndex = colCoords.leftToIndex(positionLeft);
      let slatIndex = slatCoords.positions.topToIndex(positionTop);
      if (colIndex != null && slatIndex != null) {
        let cell = this.props.cells[colIndex];
        let slatTop = slatCoords.positions.tops[slatIndex];
        let slatHeight = slatCoords.positions.getHeight(slatIndex);
        let partial = (positionTop - slatTop) / slatHeight;
        let localSnapIndex = Math.floor(partial * snapsPerSlot);
        let snapIndex = slatIndex * snapsPerSlot + localSnapIndex;
        let dayDate = this.props.cells[colIndex].date;
        let time = addDurations(dateProfile.slotMinTime, multiplyDuration(snapDuration, snapIndex));
        let start = dateEnv.add(dayDate, time);
        let end = dateEnv.add(start, snapDuration);
        return {
          dateProfile,
          dateSpan: Object.assign({ range: { start, end }, allDay: false }, cell.extraDateSpan),
          dayEl: colCoords.els[colIndex],
          rect: {
            left: colCoords.lefts[colIndex],
            right: colCoords.rights[colIndex],
            top: slatTop,
            bottom: slatTop + slatHeight
          },
          layer: 0
        };
      }
      return null;
    }
  };
  function processSlotOptions(slotDuration, snapDurationOverride) {
    let snapDuration = snapDurationOverride || slotDuration;
    let snapsPerSlot = wholeDivideDurations(slotDuration, snapDuration);
    if (snapsPerSlot === null) {
      snapDuration = slotDuration;
      snapsPerSlot = 1;
    }
    return { snapDuration, snapsPerSlot };
  }
  var DayTimeColsSlicer = class extends Slicer {
    sliceRange(range, dayRanges) {
      let segs = [];
      for (let col = 0; col < dayRanges.length; col += 1) {
        let segRange = intersectRanges(range, dayRanges[col]);
        if (segRange) {
          segs.push({
            start: segRange.start,
            end: segRange.end,
            isStart: segRange.start.valueOf() === range.start.valueOf(),
            isEnd: segRange.end.valueOf() === range.end.valueOf(),
            col
          });
        }
      }
      return segs;
    }
  };
  var DayTimeCols = class extends DateComponent {
    constructor() {
      super(...arguments);
      this.buildDayRanges = memoize(buildDayRanges);
      this.slicer = new DayTimeColsSlicer();
      this.timeColsRef = d();
    }
    render() {
      let { props, context } = this;
      let { dateProfile, dayTableModel } = props;
      let { nowIndicator, nextDayThreshold } = context.options;
      let dayRanges = this.buildDayRanges(dayTableModel, dateProfile, context.dateEnv);
      return y(NowTimer, { unit: nowIndicator ? "minute" : "day" }, (nowDate, todayRange) => y(TimeCols, Object.assign({ ref: this.timeColsRef }, this.slicer.sliceProps(props, dateProfile, null, context, dayRanges), { forPrint: props.forPrint, axis: props.axis, dateProfile, slatMetas: props.slatMetas, slotDuration: props.slotDuration, cells: dayTableModel.cells[0], tableColGroupNode: props.tableColGroupNode, tableMinWidth: props.tableMinWidth, clientWidth: props.clientWidth, clientHeight: props.clientHeight, expandRows: props.expandRows, nowDate, nowIndicatorSegs: nowIndicator && this.slicer.sliceNowDate(nowDate, dateProfile, nextDayThreshold, context, dayRanges), todayRange, onScrollTopRequest: props.onScrollTopRequest, onSlatCoords: props.onSlatCoords })));
    }
  };
  function buildDayRanges(dayTableModel, dateProfile, dateEnv) {
    let ranges = [];
    for (let date of dayTableModel.headerDates) {
      ranges.push({
        start: dateEnv.add(date, dateProfile.slotMinTime),
        end: dateEnv.add(date, dateProfile.slotMaxTime)
      });
    }
    return ranges;
  }
  var STOCK_SUB_DURATIONS = [
    { hours: 1 },
    { minutes: 30 },
    { minutes: 15 },
    { seconds: 30 },
    { seconds: 15 }
  ];
  function buildSlatMetas(slotMinTime, slotMaxTime, explicitLabelInterval, slotDuration, dateEnv) {
    let dayStart = new Date(0);
    let slatTime = slotMinTime;
    let slatIterator = createDuration(0);
    let labelInterval = explicitLabelInterval || computeLabelInterval(slotDuration);
    let metas = [];
    while (asRoughMs(slatTime) < asRoughMs(slotMaxTime)) {
      let date = dateEnv.add(dayStart, slatTime);
      let isLabeled = wholeDivideDurations(slatIterator, labelInterval) !== null;
      metas.push({
        date,
        time: slatTime,
        key: date.toISOString(),
        isoTimeStr: formatIsoTimeString(date),
        isLabeled
      });
      slatTime = addDurations(slatTime, slotDuration);
      slatIterator = addDurations(slatIterator, slotDuration);
    }
    return metas;
  }
  function computeLabelInterval(slotDuration) {
    let i3;
    let labelInterval;
    let slotsPerLabel;
    for (i3 = STOCK_SUB_DURATIONS.length - 1; i3 >= 0; i3 -= 1) {
      labelInterval = createDuration(STOCK_SUB_DURATIONS[i3]);
      slotsPerLabel = wholeDivideDurations(labelInterval, slotDuration);
      if (slotsPerLabel !== null && slotsPerLabel > 1) {
        return labelInterval;
      }
    }
    return slotDuration;
  }
  var DayTimeColsView = class extends TimeColsView {
    constructor() {
      super(...arguments);
      this.buildTimeColsModel = memoize(buildTimeColsModel);
      this.buildSlatMetas = memoize(buildSlatMetas);
    }
    render() {
      let { options, dateEnv, dateProfileGenerator } = this.context;
      let { props } = this;
      let { dateProfile } = props;
      let dayTableModel = this.buildTimeColsModel(dateProfile, dateProfileGenerator);
      let splitProps = this.allDaySplitter.splitProps(props);
      let slatMetas = this.buildSlatMetas(dateProfile.slotMinTime, dateProfile.slotMaxTime, options.slotLabelInterval, options.slotDuration, dateEnv);
      let { dayMinWidth } = options;
      let hasAttachedAxis = !dayMinWidth;
      let hasDetachedAxis = dayMinWidth;
      let headerContent = options.dayHeaders && y(DayHeader, { dates: dayTableModel.headerDates, dateProfile, datesRepDistinctDays: true, renderIntro: hasAttachedAxis ? this.renderHeadAxis : null });
      let allDayContent = options.allDaySlot !== false && ((contentArg) => y(DayTable, Object.assign({}, splitProps.allDay, { dateProfile, dayTableModel, nextDayThreshold: options.nextDayThreshold, tableMinWidth: contentArg.tableMinWidth, colGroupNode: contentArg.tableColGroupNode, renderRowIntro: hasAttachedAxis ? this.renderTableRowAxis : null, showWeekNumbers: false, expandRows: false, headerAlignElRef: this.headerElRef, clientWidth: contentArg.clientWidth, clientHeight: contentArg.clientHeight, forPrint: props.forPrint }, this.getAllDayMaxEventProps())));
      let timeGridContent = (contentArg) => y(DayTimeCols, Object.assign({}, splitProps.timed, { dayTableModel, dateProfile, axis: hasAttachedAxis, slotDuration: options.slotDuration, slatMetas, forPrint: props.forPrint, tableColGroupNode: contentArg.tableColGroupNode, tableMinWidth: contentArg.tableMinWidth, clientWidth: contentArg.clientWidth, clientHeight: contentArg.clientHeight, onSlatCoords: this.handleSlatCoords, expandRows: contentArg.expandRows, onScrollTopRequest: this.handleScrollTopRequest }));
      return hasDetachedAxis ? this.renderHScrollLayout(headerContent, allDayContent, timeGridContent, dayTableModel.colCnt, dayMinWidth, slatMetas, this.state.slatCoords) : this.renderSimpleLayout(headerContent, allDayContent, timeGridContent);
    }
  };
  function buildTimeColsModel(dateProfile, dateProfileGenerator) {
    let daySeries = new DaySeriesModel(dateProfile.renderRange, dateProfileGenerator);
    return new DayTableModel(daySeries, false);
  }
  var css_248z3 = '.fc-v-event{background-color:var(--fc-event-bg-color);border:1px solid var(--fc-event-border-color);display:block}.fc-v-event .fc-event-main{color:var(--fc-event-text-color);height:100%}.fc-v-event .fc-event-main-frame{display:flex;flex-direction:column;height:100%}.fc-v-event .fc-event-time{flex-grow:0;flex-shrink:0;max-height:100%;overflow:hidden}.fc-v-event .fc-event-title-container{flex-grow:1;flex-shrink:1;min-height:0}.fc-v-event .fc-event-title{bottom:0;max-height:100%;overflow:hidden;top:0}.fc-v-event:not(.fc-event-start){border-top-left-radius:0;border-top-right-radius:0;border-top-width:0}.fc-v-event:not(.fc-event-end){border-bottom-left-radius:0;border-bottom-right-radius:0;border-bottom-width:0}.fc-v-event.fc-event-selected:before{left:-10px;right:-10px}.fc-v-event .fc-event-resizer-start{cursor:n-resize}.fc-v-event .fc-event-resizer-end{cursor:s-resize}.fc-v-event:not(.fc-event-selected) .fc-event-resizer{height:var(--fc-event-resizer-thickness);left:0;right:0}.fc-v-event:not(.fc-event-selected) .fc-event-resizer-start{top:calc(var(--fc-event-resizer-thickness)/-2)}.fc-v-event:not(.fc-event-selected) .fc-event-resizer-end{bottom:calc(var(--fc-event-resizer-thickness)/-2)}.fc-v-event.fc-event-selected .fc-event-resizer{left:50%;margin-left:calc(var(--fc-event-resizer-dot-total-width)/-2)}.fc-v-event.fc-event-selected .fc-event-resizer-start{top:calc(var(--fc-event-resizer-dot-total-width)/-2)}.fc-v-event.fc-event-selected .fc-event-resizer-end{bottom:calc(var(--fc-event-resizer-dot-total-width)/-2)}.fc .fc-timegrid .fc-daygrid-body{z-index:2}.fc .fc-timegrid-divider{padding:0 0 2px}.fc .fc-timegrid-body{min-height:100%;position:relative;z-index:1}.fc .fc-timegrid-axis-chunk{position:relative}.fc .fc-timegrid-axis-chunk>table,.fc .fc-timegrid-slots{position:relative;z-index:1}.fc .fc-timegrid-slot{border-bottom:0;height:1.5em}.fc .fc-timegrid-slot:empty:before{content:"\\00a0"}.fc .fc-timegrid-slot-minor{border-top-style:dotted}.fc .fc-timegrid-slot-label-cushion{display:inline-block;white-space:nowrap}.fc .fc-timegrid-slot-label{vertical-align:middle}.fc .fc-timegrid-axis-cushion,.fc .fc-timegrid-slot-label-cushion{padding:0 4px}.fc .fc-timegrid-axis-frame-liquid{height:100%}.fc .fc-timegrid-axis-frame{align-items:center;display:flex;justify-content:flex-end;overflow:hidden}.fc .fc-timegrid-axis-cushion{flex-shrink:0;max-width:60px}.fc-direction-ltr .fc-timegrid-slot-label-frame{text-align:right}.fc-direction-rtl .fc-timegrid-slot-label-frame{text-align:left}.fc-liquid-hack .fc-timegrid-axis-frame-liquid{bottom:0;height:auto;left:0;position:absolute;right:0;top:0}.fc .fc-timegrid-col.fc-day-today{background-color:var(--fc-today-bg-color)}.fc .fc-timegrid-col-frame{min-height:100%;position:relative}.fc-media-screen.fc-liquid-hack .fc-timegrid-col-frame{bottom:0;height:auto;left:0;position:absolute;right:0;top:0}.fc-media-screen .fc-timegrid-cols{bottom:0;left:0;position:absolute;right:0;top:0}.fc-media-screen .fc-timegrid-cols>table{height:100%}.fc-media-screen .fc-timegrid-col-bg,.fc-media-screen .fc-timegrid-col-events,.fc-media-screen .fc-timegrid-now-indicator-container{left:0;position:absolute;right:0;top:0}.fc .fc-timegrid-col-bg{z-index:2}.fc .fc-timegrid-col-bg .fc-non-business{z-index:1}.fc .fc-timegrid-col-bg .fc-bg-event{z-index:2}.fc .fc-timegrid-col-bg .fc-highlight{z-index:3}.fc .fc-timegrid-bg-harness{left:0;position:absolute;right:0}.fc .fc-timegrid-col-events{z-index:3}.fc .fc-timegrid-now-indicator-container{bottom:0;overflow:hidden}.fc-direction-ltr .fc-timegrid-col-events{margin:0 2.5% 0 2px}.fc-direction-rtl .fc-timegrid-col-events{margin:0 2px 0 2.5%}.fc-timegrid-event-harness{position:absolute}.fc-timegrid-event-harness>.fc-timegrid-event{bottom:0;left:0;position:absolute;right:0;top:0}.fc-timegrid-event-harness-inset .fc-timegrid-event,.fc-timegrid-event.fc-event-mirror,.fc-timegrid-more-link{box-shadow:0 0 0 1px var(--fc-page-bg-color)}.fc-timegrid-event,.fc-timegrid-more-link{border-radius:3px;font-size:var(--fc-small-font-size)}.fc-timegrid-event{margin-bottom:1px}.fc-timegrid-event .fc-event-main{padding:1px 1px 0}.fc-timegrid-event .fc-event-time{font-size:var(--fc-small-font-size);margin-bottom:1px;white-space:nowrap}.fc-timegrid-event-short .fc-event-main-frame{flex-direction:row;overflow:hidden}.fc-timegrid-event-short .fc-event-time:after{content:"\\00a0-\\00a0"}.fc-timegrid-event-short .fc-event-title{font-size:var(--fc-small-font-size)}.fc-timegrid-more-link{background:var(--fc-more-link-bg-color);color:var(--fc-more-link-text-color);cursor:pointer;margin-bottom:1px;position:absolute;z-index:9999}.fc-timegrid-more-link-inner{padding:3px 2px;top:0}.fc-direction-ltr .fc-timegrid-more-link{right:0}.fc-direction-rtl .fc-timegrid-more-link{left:0}.fc .fc-timegrid-now-indicator-arrow,.fc .fc-timegrid-now-indicator-line{pointer-events:none}.fc .fc-timegrid-now-indicator-line{border-color:var(--fc-now-indicator-color);border-style:solid;border-width:1px 0 0;left:0;position:absolute;right:0;z-index:4}.fc .fc-timegrid-now-indicator-arrow{border-color:var(--fc-now-indicator-color);border-style:solid;margin-top:-5px;position:absolute;z-index:4}.fc-direction-ltr .fc-timegrid-now-indicator-arrow{border-bottom-color:transparent;border-top-color:transparent;border-width:5px 0 5px 6px;left:0}.fc-direction-rtl .fc-timegrid-now-indicator-arrow{border-bottom-color:transparent;border-top-color:transparent;border-width:5px 6px 5px 0;right:0}';
  injectStyles(css_248z3);

  // ../ifitwala_ed/node_modules/@fullcalendar/timegrid/index.js
  var OPTION_REFINERS = {
    allDaySlot: Boolean
  };
  var index2 = createPlugin({
    name: "@fullcalendar/timegrid",
    initialView: "timeGridWeek",
    optionRefiners: OPTION_REFINERS,
    views: {
      timeGrid: {
        component: DayTimeColsView,
        usesMinMaxTime: true,
        allDaySlot: true,
        slotDuration: "00:30:00",
        slotEventOverlap: true
      },
      timeGridDay: {
        type: "timeGrid",
        duration: { days: 1 }
      },
      timeGridWeek: {
        type: "timeGrid",
        duration: { weeks: 1 }
      }
    }
  });

  // ../ifitwala_ed/node_modules/@fullcalendar/list/internal.js
  var ListViewHeaderRow = class extends BaseComponent {
    constructor() {
      super(...arguments);
      this.state = {
        textId: getUniqueDomId()
      };
    }
    render() {
      let { theme, dateEnv, options, viewApi } = this.context;
      let { cellId, dayDate, todayRange } = this.props;
      let { textId } = this.state;
      let dayMeta = getDateMeta(dayDate, todayRange);
      let text = options.listDayFormat ? dateEnv.format(dayDate, options.listDayFormat) : "";
      let sideText = options.listDaySideFormat ? dateEnv.format(dayDate, options.listDaySideFormat) : "";
      let renderProps = Object.assign({
        date: dateEnv.toDate(dayDate),
        view: viewApi,
        textId,
        text,
        sideText,
        navLinkAttrs: buildNavLinkAttrs(this.context, dayDate),
        sideNavLinkAttrs: buildNavLinkAttrs(this.context, dayDate, "day", false)
      }, dayMeta);
      return y(ContentContainer, { elTag: "tr", elClasses: [
        "fc-list-day",
        ...getDayClassNames(dayMeta, theme)
      ], elAttrs: {
        "data-date": formatDayString(dayDate)
      }, renderProps, generatorName: "dayHeaderContent", customGenerator: options.dayHeaderContent, defaultGenerator: renderInnerContent4, classNameGenerator: options.dayHeaderClassNames, didMount: options.dayHeaderDidMount, willUnmount: options.dayHeaderWillUnmount }, (InnerContent) => y(
        "th",
        { scope: "colgroup", colSpan: 3, id: cellId, "aria-labelledby": textId },
        y(InnerContent, { elTag: "div", elClasses: [
          "fc-list-day-cushion",
          theme.getClass("tableCellShaded")
        ] })
      ));
    }
  };
  function renderInnerContent4(props) {
    return y(
      _,
      null,
      props.text && y("a", Object.assign({ id: props.textId, className: "fc-list-day-text" }, props.navLinkAttrs), props.text),
      props.sideText && y("a", Object.assign({ "aria-hidden": true, className: "fc-list-day-side-text" }, props.sideNavLinkAttrs), props.sideText)
    );
  }
  var DEFAULT_TIME_FORMAT2 = createFormatter({
    hour: "numeric",
    minute: "2-digit",
    meridiem: "short"
  });
  var ListViewEventRow = class extends BaseComponent {
    render() {
      let { props, context } = this;
      let { options } = context;
      let { seg, timeHeaderId, eventHeaderId, dateHeaderId } = props;
      let timeFormat = options.eventTimeFormat || DEFAULT_TIME_FORMAT2;
      return y(EventContainer, Object.assign({}, props, { elTag: "tr", elClasses: [
        "fc-list-event",
        seg.eventRange.def.url && "fc-event-forced-url"
      ], defaultGenerator: () => renderEventInnerContent(seg, context), seg, timeText: "", disableDragging: true, disableResizing: true }), (InnerContent, eventContentArg) => y(
        _,
        null,
        buildTimeContent(seg, timeFormat, context, timeHeaderId, dateHeaderId),
        y(
          "td",
          { "aria-hidden": true, className: "fc-list-event-graphic" },
          y("span", { className: "fc-list-event-dot", style: {
            borderColor: eventContentArg.borderColor || eventContentArg.backgroundColor
          } })
        ),
        y(InnerContent, { elTag: "td", elClasses: ["fc-list-event-title"], elAttrs: { headers: `${eventHeaderId} ${dateHeaderId}` } })
      ));
    }
  };
  function renderEventInnerContent(seg, context) {
    let interactiveAttrs = getSegAnchorAttrs(seg, context);
    return y("a", Object.assign({}, interactiveAttrs), seg.eventRange.def.title);
  }
  function buildTimeContent(seg, timeFormat, context, timeHeaderId, dateHeaderId) {
    let { options } = context;
    if (options.displayEventTime !== false) {
      let eventDef = seg.eventRange.def;
      let eventInstance = seg.eventRange.instance;
      let doAllDay = false;
      let timeText;
      if (eventDef.allDay) {
        doAllDay = true;
      } else if (isMultiDayRange(seg.eventRange.range)) {
        if (seg.isStart) {
          timeText = buildSegTimeText(seg, timeFormat, context, null, null, eventInstance.range.start, seg.end);
        } else if (seg.isEnd) {
          timeText = buildSegTimeText(seg, timeFormat, context, null, null, seg.start, eventInstance.range.end);
        } else {
          doAllDay = true;
        }
      } else {
        timeText = buildSegTimeText(seg, timeFormat, context);
      }
      if (doAllDay) {
        let renderProps = {
          text: context.options.allDayText,
          view: context.viewApi
        };
        return y(ContentContainer, { elTag: "td", elClasses: ["fc-list-event-time"], elAttrs: {
          headers: `${timeHeaderId} ${dateHeaderId}`
        }, renderProps, generatorName: "allDayContent", customGenerator: options.allDayContent, defaultGenerator: renderAllDayInner2, classNameGenerator: options.allDayClassNames, didMount: options.allDayDidMount, willUnmount: options.allDayWillUnmount });
      }
      return y("td", { className: "fc-list-event-time" }, timeText);
    }
    return null;
  }
  function renderAllDayInner2(renderProps) {
    return renderProps.text;
  }
  var ListView = class extends DateComponent {
    constructor() {
      super(...arguments);
      this.computeDateVars = memoize(computeDateVars);
      this.eventStoreToSegs = memoize(this._eventStoreToSegs);
      this.state = {
        timeHeaderId: getUniqueDomId(),
        eventHeaderId: getUniqueDomId(),
        dateHeaderIdRoot: getUniqueDomId()
      };
      this.setRootEl = (rootEl) => {
        if (rootEl) {
          this.context.registerInteractiveComponent(this, {
            el: rootEl
          });
        } else {
          this.context.unregisterInteractiveComponent(this);
        }
      };
    }
    render() {
      let { props, context } = this;
      let { dayDates, dayRanges } = this.computeDateVars(props.dateProfile);
      let eventSegs = this.eventStoreToSegs(props.eventStore, props.eventUiBases, dayRanges);
      return y(
        ViewContainer,
        { elRef: this.setRootEl, elClasses: [
          "fc-list",
          context.theme.getClass("table"),
          context.options.stickyHeaderDates !== false ? "fc-list-sticky" : ""
        ], viewSpec: context.viewSpec },
        y(Scroller, { liquid: !props.isHeightAuto, overflowX: props.isHeightAuto ? "visible" : "hidden", overflowY: props.isHeightAuto ? "visible" : "auto" }, eventSegs.length > 0 ? this.renderSegList(eventSegs, dayDates) : this.renderEmptyMessage())
      );
    }
    renderEmptyMessage() {
      let { options, viewApi } = this.context;
      let renderProps = {
        text: options.noEventsText,
        view: viewApi
      };
      return y(ContentContainer, { elTag: "div", elClasses: ["fc-list-empty"], renderProps, generatorName: "noEventsContent", customGenerator: options.noEventsContent, defaultGenerator: renderNoEventsInner, classNameGenerator: options.noEventsClassNames, didMount: options.noEventsDidMount, willUnmount: options.noEventsWillUnmount }, (InnerContent) => y(InnerContent, { elTag: "div", elClasses: ["fc-list-empty-cushion"] }));
    }
    renderSegList(allSegs, dayDates) {
      let { theme, options } = this.context;
      let { timeHeaderId, eventHeaderId, dateHeaderIdRoot } = this.state;
      let segsByDay = groupSegsByDay(allSegs);
      return y(NowTimer, { unit: "day" }, (nowDate, todayRange) => {
        let innerNodes = [];
        for (let dayIndex = 0; dayIndex < segsByDay.length; dayIndex += 1) {
          let daySegs = segsByDay[dayIndex];
          if (daySegs) {
            let dayStr = formatDayString(dayDates[dayIndex]);
            let dateHeaderId = dateHeaderIdRoot + "-" + dayStr;
            innerNodes.push(y(ListViewHeaderRow, { key: dayStr, cellId: dateHeaderId, dayDate: dayDates[dayIndex], todayRange }));
            daySegs = sortEventSegs(daySegs, options.eventOrder);
            for (let seg of daySegs) {
              innerNodes.push(y(ListViewEventRow, Object.assign({ key: dayStr + ":" + seg.eventRange.instance.instanceId, seg, isDragging: false, isResizing: false, isDateSelecting: false, isSelected: false, timeHeaderId, eventHeaderId, dateHeaderId }, getSegMeta(seg, todayRange, nowDate))));
            }
          }
        }
        return y(
          "table",
          { className: "fc-list-table " + theme.getClass("table") },
          y(
            "thead",
            null,
            y(
              "tr",
              null,
              y("th", { scope: "col", id: timeHeaderId }, options.timeHint),
              y("th", { scope: "col", "aria-hidden": true }),
              y("th", { scope: "col", id: eventHeaderId }, options.eventHint)
            )
          ),
          y("tbody", null, innerNodes)
        );
      });
    }
    _eventStoreToSegs(eventStore, eventUiBases, dayRanges) {
      return this.eventRangesToSegs(sliceEventStore(eventStore, eventUiBases, this.props.dateProfile.activeRange, this.context.options.nextDayThreshold).fg, dayRanges);
    }
    eventRangesToSegs(eventRanges, dayRanges) {
      let segs = [];
      for (let eventRange of eventRanges) {
        segs.push(...this.eventRangeToSegs(eventRange, dayRanges));
      }
      return segs;
    }
    eventRangeToSegs(eventRange, dayRanges) {
      let { dateEnv } = this.context;
      let { nextDayThreshold } = this.context.options;
      let range = eventRange.range;
      let allDay = eventRange.def.allDay;
      let dayIndex;
      let segRange;
      let seg;
      let segs = [];
      for (dayIndex = 0; dayIndex < dayRanges.length; dayIndex += 1) {
        segRange = intersectRanges(range, dayRanges[dayIndex]);
        if (segRange) {
          seg = {
            component: this,
            eventRange,
            start: segRange.start,
            end: segRange.end,
            isStart: eventRange.isStart && segRange.start.valueOf() === range.start.valueOf(),
            isEnd: eventRange.isEnd && segRange.end.valueOf() === range.end.valueOf(),
            dayIndex
          };
          segs.push(seg);
          if (!seg.isEnd && !allDay && dayIndex + 1 < dayRanges.length && range.end < dateEnv.add(dayRanges[dayIndex + 1].start, nextDayThreshold)) {
            seg.end = range.end;
            seg.isEnd = true;
            break;
          }
        }
      }
      return segs;
    }
  };
  function renderNoEventsInner(renderProps) {
    return renderProps.text;
  }
  function computeDateVars(dateProfile) {
    let dayStart = startOfDay(dateProfile.renderRange.start);
    let viewEnd = dateProfile.renderRange.end;
    let dayDates = [];
    let dayRanges = [];
    while (dayStart < viewEnd) {
      dayDates.push(dayStart);
      dayRanges.push({
        start: dayStart,
        end: addDays(dayStart, 1)
      });
      dayStart = addDays(dayStart, 1);
    }
    return { dayDates, dayRanges };
  }
  function groupSegsByDay(segs) {
    let segsByDay = [];
    let i3;
    let seg;
    for (i3 = 0; i3 < segs.length; i3 += 1) {
      seg = segs[i3];
      (segsByDay[seg.dayIndex] || (segsByDay[seg.dayIndex] = [])).push(seg);
    }
    return segsByDay;
  }
  var css_248z4 = ':root{--fc-list-event-dot-width:10px;--fc-list-event-hover-bg-color:#f5f5f5}.fc-theme-standard .fc-list{border:1px solid var(--fc-border-color)}.fc .fc-list-empty{align-items:center;background-color:var(--fc-neutral-bg-color);display:flex;height:100%;justify-content:center}.fc .fc-list-empty-cushion{margin:5em 0}.fc .fc-list-table{border-style:hidden;width:100%}.fc .fc-list-table tr>*{border-left:0;border-right:0}.fc .fc-list-sticky .fc-list-day>*{background:var(--fc-page-bg-color);position:sticky;top:0}.fc .fc-list-table thead{left:-10000px;position:absolute}.fc .fc-list-table tbody>tr:first-child th{border-top:0}.fc .fc-list-table th{padding:0}.fc .fc-list-day-cushion,.fc .fc-list-table td{padding:8px 14px}.fc .fc-list-day-cushion:after{clear:both;content:"";display:table}.fc-theme-standard .fc-list-day-cushion{background-color:var(--fc-neutral-bg-color)}.fc-direction-ltr .fc-list-day-text,.fc-direction-rtl .fc-list-day-side-text{float:left}.fc-direction-ltr .fc-list-day-side-text,.fc-direction-rtl .fc-list-day-text{float:right}.fc-direction-ltr .fc-list-table .fc-list-event-graphic{padding-right:0}.fc-direction-rtl .fc-list-table .fc-list-event-graphic{padding-left:0}.fc .fc-list-event.fc-event-forced-url{cursor:pointer}.fc .fc-list-event:hover td{background-color:var(--fc-list-event-hover-bg-color)}.fc .fc-list-event-graphic,.fc .fc-list-event-time{white-space:nowrap;width:1px}.fc .fc-list-event-dot{border:calc(var(--fc-list-event-dot-width)/2) solid var(--fc-event-border-color);border-radius:calc(var(--fc-list-event-dot-width)/2);box-sizing:content-box;display:inline-block;height:0;width:0}.fc .fc-list-event-title a{color:inherit;text-decoration:none}.fc .fc-list-event.fc-event-forced-url:hover a{text-decoration:underline}';
  injectStyles(css_248z4);

  // ../ifitwala_ed/node_modules/@fullcalendar/list/index.js
  var OPTION_REFINERS2 = {
    listDayFormat: createFalsableFormatter,
    listDaySideFormat: createFalsableFormatter,
    noEventsClassNames: identity,
    noEventsContent: identity,
    noEventsDidMount: identity,
    noEventsWillUnmount: identity
  };
  function createFalsableFormatter(input) {
    return input === false ? null : createFormatter(input);
  }
  var index3 = createPlugin({
    name: "@fullcalendar/list",
    optionRefiners: OPTION_REFINERS2,
    views: {
      list: {
        component: ListView,
        buttonTextKey: "list",
        listDayFormat: { month: "long", day: "numeric", year: "numeric" }
      },
      listDay: {
        type: "list",
        duration: { days: 1 },
        listDayFormat: { weekday: "long" }
      },
      listWeek: {
        type: "list",
        duration: { weeks: 1 },
        listDayFormat: { weekday: "long" },
        listDaySideFormat: { month: "long", day: "numeric", year: "numeric" }
      },
      listMonth: {
        type: "list",
        duration: { month: 1 },
        listDaySideFormat: { weekday: "long" }
      },
      listYear: {
        type: "list",
        duration: { year: 1 },
        listDaySideFormat: { weekday: "long" }
      }
    }
  });

  // ../ifitwala_ed/ifitwala_ed/public/js/desk_fullcalendar.js
  window.FullCalendar = { Calendar, dayGridPlugin: index, timeGridPlugin: index2, listPlugin: index3 };

  // ../ifitwala_ed/ifitwala_ed/public/js/student_group_cards.js
  function slugify(filename) {
    return filename.replace(/\.[^.]+$/, "").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  }
  function get_student_image(original_url) {
    const fallback = "/assets/ifitwala_ed/images/default_student_image.png";
    if (!original_url)
      return fallback;
    if (original_url.startsWith("/files/gallery_resized/student/"))
      return original_url;
    if (!original_url.startsWith("/files/student/"))
      return fallback;
    const base = slugify(original_url.split("/").pop());
    return `/files/gallery_resized/student/thumb_${base}.webp`;
  }
  function renderStudentCard(student, { thumbSize = 80 } = {}) {
    const student_name = frappe.utils.escape_html(student.student_name);
    const preferred_name = frappe.utils.escape_html(student.preferred_name || "");
    const student_id = frappe.utils.escape_html(student.student);
    const thumb_src = get_student_image(student.student_image);
    const fallback_src = student.student_image || "/assets/ifitwala_ed/images/default_student_image.png";
    let birthday_icon = "";
    if (student.birth_date) {
      try {
        const bdate = frappe.datetime.str_to_obj(student.birth_date);
        const today = frappe.datetime.str_to_obj(frappe.datetime.now_date());
        const thisYear = new Date(today.getFullYear(), bdate.getMonth(), bdate.getDate());
        const diffDays2 = Math.floor((thisYear - today) / 864e5);
        if (Math.abs(diffDays2) <= 5) {
          const formatted = moment(bdate).format("dddd, MMMM D");
          birthday_icon = `
					<span class="ml-2 text-yellow-500 cursor-pointer"
						onclick="frappe.msgprint('${__("Birthday:")} ${formatted}')"
						title="${__("Birthday on {0}", [formatted])}">\u{1F382}</span>`;
        }
      } catch (e3) {
      }
    }
    let health_icon = "";
    if (student.medical_info) {
      const note = frappe.utils.escape_html(student.medical_info);
      health_icon = `
			<span class="ml-2 text-red-500 font-bold cursor-pointer"
				onclick='frappe.msgprint({title:"${__("Health Note for {0}", [student_name])}",
										 message:\`${note}\`,indicator:"red"})'
				title="${__("Health Note Available")}">&#x2716;</span>`;
    }
    return `
		<div class="student-card bg-white rounded-xl p-4 text-center shadow hover:-translate-y-1 transition duration-200">
			<a href="/app/student/${student_id}" target="_blank" rel="noopener">
				<img src="${thumb_src}"
						onerror="this.onerror=null;this.src='${fallback_src}';"
						class="student-card-img"
						loading="lazy">
			</a>
			<div class="mt-3 text-lg font-semibold">
				<a href="/app/student/${student_id}" target="_blank" rel="noopener">${student_name}</a>
				${health_icon}${birthday_icon}
			</div>
			${preferred_name ? `<div class="text-sm text-gray-500 mt-1">${preferred_name}</div>` : ""}
		</div>`;
  }

  // ../ifitwala_ed/ifitwala_ed/public/js/ifitwala_ed.bundle.js
  var root = window.frappe = window.frappe || {};
  root.ifitwala_ed = root.ifitwala_ed || {};
  root.ifitwala_ed.helpers = root.ifitwala_ed.helpers || {};
  root.ifitwala_ed.helpers.renderStudentCard = renderStudentCard;
})();
//# sourceMappingURL=ifitwala_ed.bundle.AIE7GZ2W.js.map
