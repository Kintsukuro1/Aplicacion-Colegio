/*REPORTES JS*/function generarReporte(tipo){const params=new URLSearchParams({tipo,formato:'excel',periodo:'mes_actual'});window.location.href=`/api/asesor-financiero/reportes/generar/?${params}`}
