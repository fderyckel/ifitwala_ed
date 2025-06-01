
import "./utils";
import "./queries";
import "./desk_fullcalendar" 
import "../css/student_group_cards.css";

import { renderStudentCard } from "./student_group_cards.js";
frappe.provide("ifitwala_ed.helpers");
frappe.ifitwala_ed.helpers.renderStudentCard = renderStudentCard;