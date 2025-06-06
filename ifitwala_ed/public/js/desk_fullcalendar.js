/* Desk-wide FullCalendar loader
 * (one tiny bundle, shared by every desk page that needs it)
 */


import "../../../node_modules/@fullcalendar/core/index.global.css";
import "../../../node_modules/@fullcalendar/daygrid/index.global.css";
import "../../../node_modules/@fullcalendar/timegrid/index.global.css";
import "../../../node_modules/@fullcalendar/list/index.global.css";


import { Calendar } from "@fullcalendar/core";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import listPlugin from "@fullcalendar/list";



/* Make it behave like the old “index.global” build */
window.FullCalendar = { Calendar, dayGridPlugin, timeGridPlugin, listPlugin };


