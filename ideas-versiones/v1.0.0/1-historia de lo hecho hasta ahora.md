mira este entorno es un conjunto de scripts que servian para hacer cosas con revolico publicar, renovar, etc, el tema es que revolico ha ido cambiando por ejemplo lo de renovar ya no hace tanta falta pq ya ellos tienen un boton de renovar todo, lo importante es publicar anuncions nuevos, el problema es que revolico ha puesto mas fuerte las politicas antibots y se dan cuenta mas rapido cuando es un bot intentando publicar antes yse podia poner el mismo anuncio una y otra vez q no pasaba nada pero ya no, ahora hay que poner una imagen distinta y una descripcion distinta, pq si no te pueden detectar como un bot y cuando detecta bots borra los anuncios y no solo eso  es que  te banea la cuenta o el numero de telefono.

Por tanto hay que cambiar la estrategia para publicar,antes lo que yo hacia era publicar en una sola cuenta y a partir de esa cogia las cosas y las ponia en muchas cuentas mas, ahora habra que cambiar la estrategia, habra que crear por producto muchas imagenes distintas y por cada producto muchas descripciones distintas, el tema con esto es que yo ahora mismo como creo muchas imagenes es con ia pero a traves de la web ya que es gratis por tanto el proceso es lento y no automatizado, entonces aqui va mi primera duda, 

1- tienes alguna idea de como automatizar a partir de una unica imagen la creacion de muchas otras y que estas otras no puedan ser detectadas por el sistema q tiene revolico sea cual sea, por ejemplo se que invirtiendo la imagen de derecha a izquierda no las detecta como iguales, pero rotandolas a menos que la rotacion sea muy grande si que las detecta, esto para mi seria super bueno porque me ahorraria mucho trabajo

2- si esto no se puede la idea que yo tenia era crear una carpeta llamada imagenes, dntro de esa carpeta de imagenes crear subcarpetas por cada producto y dentro de cada subcarpeta crear con ia muuuuchas imagenes por cada producto, entonces digamos va quedando asi la idea

carpeta-imagenes
subcarpetas:
 buros: 20 imagenes
 colchonetas: 20 imagenes
 colchas: 20 imagenes
 ...

 entonces ya yo pongo aqui en este entorno esa carpeta con subcarpetas, entonces me gustaria tener un script que lo que hiciera fuera agrupar imagenes por cuenta, al final yo en revolico publico en cuentas, o sea cogeria por cada subproducto y le iria como que copiando cada imagen a una carpeta asociada a la cuenta, o sea cuenta 1, cuenta 2, cuenta 3 etc, y ademas de la imagen debe tener los detalles de la publicacion por ejemplo descripcion, nombre del producto y asi como se puede ver en las carpetas de anuncios  por ejemplo este, debe tener los detalles anuncios/54130535/datos.md (de aqui el id y la url no son necesarios pq eso se pone una vez se publica y yo lo que quiero es darle los datos para publicar, o sea nombre, precio descripcion y categoria) la idea es que por ejemplo yo abro una cuenta fernandoantigravity@gmail.com y a esta cuenta se le cree una publicacion por cada uno de los productos q yo tenga en la carpeta de imagenes, una vez vaya publicando productos en esta cuenta, la imagen usada que estaria dentro de una carpeta llamada cuenta "numero" debera ser marcada como que ya se uso, y tb se debe marcar de alguna manera que los productos que ya estan publicados a una determinada cuenta no se pueden volver a subir.

 resumen
 paso uno creo una carpeta imagenes
 dentro de ella creo las carpetas de productos y tb se debe crear un .md que asocie la cuenta usada con los productos que se han subido a ella asi cuando se vuelva a abrir esta cuenta no se publiquen de nuevo las cosas que ya se han publicado si no otras cosas nuevas
 dentro de las subcarpetas de productos, llamadas por ejemplo mesita de noche, refrigeradores, candelabros etc, se debe crear dentro subcarpetas llamadas cuenta 1, cuanta 2, con el objetivo de que la primera ccon la qque yo empiece a publicar use las imagenes desde la 1, y una vez publique se marque como usada y ya no se vuelva a usar. tb dentro de estas subcarpetas de producto debe haber un md que sea el que de los detalles del producto, como su nombre, precio, descripcion y categoria, entonces ahi habria que pedirle a ala ia que replicase ese md en cada una de las carpetas de cuenta 1 cuenta 2 etc cambiando un poco la descripcion para que no sea exactamente igual.

 otra idea de hacer lo mismo es en cambio que el script en lugar de meter una carpeta cuenta dentro de cada carpeta de subproducto cree directamente carpetas cuenta dentro de la carpeta imagenes y meta ahi los subproductosq le corresponden a esa cuenta que seria uno de cada uno y una vez  se comience a publicar se vea que cuenta es la que esta publicando se asocie a la carpeta cuenta desde la q esta publicando y que esa cuenta por ejemplo fernandoantigravity@gmail.com si es la primera en la que empece a publicar se asocie a cuenta uno, vaya tachando los artiuclos publicados como que ya se publicaron o sea ya no se puedan volver a publicar y esa cuenta solo pueda publicar las cosas de la cuenta a la que se asocio,

 no se dime tu cual crees que sea la mejor idea?

 lo mas importante de esta idea es que no puedan saber que es un bot asi que hay que tomar tanta precaucion sea posible por ejemplo en caso de que salga lo de que cloudflare te pide marcar un casillero no se q es lo mejor si cerrar la pagina o quedarse sin hacer nada, lo mejor para que no detecte que es un bot

 y la otra cosa es que hasta ahora he estado usando playwright, pero lei que esto se podia detectar que era un bot mas facil que si fuera una extension como lo es  /home/camiloueransim/maybel-ventas/renovar-anuncios/RevoRenew last update, bueno dejame decirte que antes cuando usaba los cripts de aqui con playwright para renovar revolico los empezo a detectar y a mandar muchas verificaciones de cloudflare pero con el paso del tiempo incluso a revo renew le empezaron a mandar verificaciones de cloudflare entonces no se realente cual es el mejor metodo para hacer esto de las verificaciones de cloudflare y que no nos detecten como bot?


si quieres entender mejor que aplicacion yo usaba para publicar mira en  /home/camiloueransim/maybel-ventas/renovar-anuncios/publicar sobre todo /home/camiloueransim/maybel-ventas/renovar-anuncios/publicar/publicar_anuncios_precio_original-fast.py que era el ultimo q estaba usando q servia bien
 