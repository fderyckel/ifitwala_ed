/* Desk-wide FullCalendar loader
 * (one tiny bundle, shared by every desk page that needs it)
 */


import { Calendar }      from "@fullcalendar/core";
import dayGridPlugin     from "@fullcalendar/daygrid";
import timeGridPlugin    from "@fullcalendar/timegrid";
import listPlugin        from "@fullcalendar/list";

/* CSS for all three view plugins */
import "@fullcalendar/core/index.css";
import "@fullcalendar/daygrid/index.css";
import "@fullcalendar/timegrid/index.css";
import "@fullcalendar/list/index.css";

/* Make it behave like the old “index.global” build */
window.FullCalendar = { Calendar, dayGridPlugin, timeGridPlugin, listPlugin };


