
import "./utils";
import "./queries";
import "./desk_fullcalendar" 
import "../css/student_group_cards.css";

import { renderStudentCard } from "./student_group_cards.js";

// -- Make sure the namespace exists even if Frappe JS isn't loaded yet
const root = (window.frappe = window.frappe || {});      // guarantee global frappe
root.ifitwala_ed = root.ifitwala_ed || {};
root.ifitwala_ed.helpers = root.ifitwala_ed.helpers || {};
root.ifitwala_ed.helpers.renderStudentCard = renderStudentCard;