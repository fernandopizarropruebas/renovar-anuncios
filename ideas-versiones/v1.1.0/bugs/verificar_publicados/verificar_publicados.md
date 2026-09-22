el de verificar publicados no esta funcionando del todo bien, pq mira por ejemplo me dice         que confirma 125 vivos aunq en realidad hay solo 119 q es lo q me dice revolico ──────────────────────────────────────────────────
  📊 Resumen — alejandroantigravity2@gmail.com
  ──────────────────────────────────────────────────
  ✅ Vivos confirmados                   : 125
  ❌ Borrados/Despublicados por Revolico  : 5
  📦 Total en estado 'publicado'          : 130
  🌐 Total anuncios en /account/ads       : 119

  mira los que la doble verificacion dijo q estaban pero en realidad no estaban junto a los que la doble verificacion si dijo bien q no estaban


La cuenta fue alejandroantigravity2@gmail.com y mira lo q dice la doble verificacion en esos anuncios
───────────────────────────────
  🔍 DOBLE VERIFICACIÓN
  ──────────────────────────────────────────────────

    [1/11] Estante de cocina (ID 57380354)
      🔍 Doble verificación para ID 57380354...
      ✅ Falsa Alarma: La URL cargó correctamente. Sigue vivo.

    [2/11] Lampara (ID 57555599)
      🔍 Doble verificación para ID 57555599...
      ✅ Falsa Alarma: La URL cargó correctamente. Sigue vivo.

    [3/11] Maquina de hacer hielo (ID 57555621)
      🔍 Doble verificación para ID 57555621...
      ✅ Falsa Alarma: La URL cargó correctamente. Sigue vivo.

    [4/11] Maquina de hielo (ID 57555650)
      🔍 Doble verificación para ID 57555650...
      ✅ Falsa Alarma: La URL cargó correctamente. Sigue vivo.

    [5/11] Maquinas de hacer hielo (ID 57555665)
      🔍 Doble verificación para ID 57555665...
      ✅ Falsa Alarma: La URL cargó correctamente. Sigue vivo.

    [6/11] Maquinas de hielo (ID 57555686)
      🔍 Doble verificación para ID 57555686...
      ✅ Falsa Alarma: La URL cargó correctamente. Sigue vivo.

    [7/11] bicicletas medida 12 (ID 57586174)
      🔍 Doble verificación para ID 57586174...
      ❌ Confirmado: Dice 'Anuncio despublicado'

    [8/11] carpa (ID 57586525)
      🔍 Doble verificación para ID 57586525...
      ❌ Confirmado: Dice 'Anuncio despublicado'

    [9/11] carpas (ID 57590338)
      🔍 Doble verificación para ID 57590338...
      ❌ Confirmado: Dice 'Anuncio despublicado'

    [10/11] mesas de noche inteligente (ID 57590919)
      🔍 Doble verificación para ID 57590919...
      ❌ Confirmado: Dice 'Anuncio despublicado'

    [11/11] mesas_de_escritorio-140cm (ID 57590986)
      🔍 Doble verificación para ID 57590986...
      ❌ Confirmado: Dice 'Anuncio despublicado'


no se pq esta haciendo esto mal, quizas es pq esta buscando   mal las url pq hay veces q revolico le responde no tienes permiso a esta pagina como en esta imagen /home/camiloueransim/maybel-ventas/renovar-anuncios/ideas-versiones/v1.1.0/bugs/verificar_publicados/image1.jpg en lugar de  decir deespublicado, lo q si me di cuenta es que en las url de estos productos cuando revise en /home/camiloueransim/maybel-ventas/renovar-anuncios/estado/cuentas/alejandroantigravity2@gmail.com.json los productos estos que la doble verificacion dijo q estaban aun pero q en realidad no estaban, al final de la url no decia action=created por ejemplo mira 
   {
      "producto": "Maquinas de hielo",
      "imagenes_usadas": [
        "variantes_WhatsApp Image 2026-09-18 at 12.08.29 AM/WhatsApp Image 2026-09-18 at 12.08.29 AM_v001.jpg"
      ],
      "descripcion_usada": "variante_001.txt",
      "fecha_asignacion": "2026-09-21T09:47:24.674283",
      "estado": "publicado",
      "url_revolico": "https://www.revolico.com/item/57555686/_/manage",
      "fecha_publicacion": "2026-09-21T10:11:44.506995",
      "fecha_deteccion_borrado": "2026-09-21T17:53:03.937092"
    },
, eso si me gustaria q cuando se verficara los anuncios cuando se busque la url se quede hasta el manage y no hasta el action created. mira por ejemplo cuando busque en la doble verificacion https://www.revolico.com/item/57585569/_/manage?action=created solo busque hasta https://www.revolico.com/item/57585569/_/manage no vaya a ser q por poner hasta el action created se de cuenta de q es un bot
