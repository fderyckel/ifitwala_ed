
import "./utils";
import "./queries";
import "./desk_fullcalendar"
import { renderStudentCard } from "./student_group_cards.js";   
import "../css/student_group_cards.css";

frappe.renderStudentCard = renderStudentCard;
