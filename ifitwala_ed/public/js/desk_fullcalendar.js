/* Desk-wide FullCalendar loader
 * (one tiny bundle, shared by every desk page that needs it)
 */


import { Calendar } from "@fullcalendar/core";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import listPlugin from "@fullcalendar/list";






/* Make it behave like the old “index.global” build */
window.FullCalendar = { Calendar, dayGridPlugin, timeGridPlugin, listPlugin };


