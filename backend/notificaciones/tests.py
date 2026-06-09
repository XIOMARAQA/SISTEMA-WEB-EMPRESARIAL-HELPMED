from django.contrib.auth import get_user_model
from django.test import TestCase

from notificaciones.destinatarios import DESTINATARIOS
from notificaciones.flujos import (
    notificar_alerta_login,
    notificar_discrepancia_inventario,
    notificar_documentacion_rechazada,
    notificar_factura_registrada,
    notificar_movimiento_inventario,
)
from notificaciones.models import Notificacion
from notificaciones.services import destinatarios_notificacion, notificar_por_roles
from seguridad.models import Rol, UsuarioRol

User = get_user_model()


class NotificacionesPorRolTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.roles = {}
        for codigo in (
            'admin', 'jefe_compras', 'jefe_almacen', 'operario_almacen',
            'encargado_calidad', 'jefe_operaciones', 'area_administrativa', 'gerente_general',
        ):
            cls.roles[codigo], _ = Rol.objects.get_or_create(
                codigo=codigo,
                defaults={'nombre': codigo, 'activo': True},
            )

        cls.admin = User.objects.create_user(
            username='admin_notif', password='x', email='a@test.com',
            nombres='Admin', apellidos='Test', documento='90000001',
            is_superuser=True, is_staff=True,
        )
        cls.jefe_compras = cls._usuario('jcompras', '90000002', 'jefe_compras')
        cls.jefe_almacen = cls._usuario('jalmacen', '90000003', 'jefe_almacen')
        cls.operario = cls._usuario('operario', '90000004', 'operario_almacen')
        cls.calidad = cls._usuario('calidad', '90000005', 'encargado_calidad')
        cls.area_admin = cls._usuario('areaadm', '90000006', 'area_administrativa')

    @classmethod
    def _usuario(cls, username, doc, rol_codigo):
        user = User.objects.create_user(
            username=username,
            password='x',
            email=f'{username}@test.com',
            nombres=username,
            apellidos='Test',
            documento=doc,
        )
        UsuarioRol.objects.create(usuario=user, rol=cls.roles[rol_codigo])
        return user

    def test_admin_recibe_todas_las_notificaciones(self):
        notificar_por_roles(
            ['jefe_almacen'],
            titulo='Prueba admin',
            mensaje='Mensaje de prueba',
        )
        self.assertTrue(
            Notificacion.objects.filter(usuario=self.admin, titulo='Prueba admin').exists()
        )
        self.assertTrue(
            Notificacion.objects.filter(usuario=self.jefe_almacen, titulo='Prueba admin').exists()
        )
        self.assertFalse(
            Notificacion.objects.filter(usuario=self.jefe_compras, titulo='Prueba admin').exists()
        )

    def test_factura_registrada_solo_almacen_y_admin(self):
        class OrdenFake:
            id = 1
            numero_completo = 'F001-000001'

            class proveedor:
                razon_social = 'Proveedor Test'

        notificar_factura_registrada(OrdenFake(), actor=self.jefe_compras)
        dest = {u.username for u in destinatarios_notificacion(DESTINATARIOS['factura_registrada'])}
        self.assertIn('jalmacen', dest)
        self.assertIn('admin_notif', dest)
        self.assertNotIn('jcompras', dest)

    def test_documentacion_rechazada_solo_compras_y_admin(self):
        class OrdenFake:
            id = 2
            numero_completo = 'F001-000002'
            motivo_rechazo = 'Falta guía'

        notificar_documentacion_rechazada(OrdenFake(), actor=self.jefe_almacen)
        self.assertTrue(
            Notificacion.objects.filter(
                usuario=self.jefe_compras,
                titulo='Factura rechazada — documentación incompleta',
            ).exists()
        )
        self.assertFalse(
            Notificacion.objects.filter(
                usuario=self.jefe_almacen,
                titulo='Factura rechazada — documentación incompleta',
            ).exists()
        )

    def test_discrepancia_area_administrativa_y_almacen(self):
        class InvFake:
            id = 10
            cantidad = 100
            cantidad_fisica = 90
            lote = 'L001'

            class producto:
                nombre = 'Paracetamol'

        notificar_discrepancia_inventario(InvFake(), actor=self.operario)
        self.assertTrue(
            Notificacion.objects.filter(usuario=self.area_admin).exists()
        )
        self.assertTrue(
            Notificacion.objects.filter(usuario=self.jefe_almacen).exists()
        )
        self.assertFalse(
            Notificacion.objects.filter(usuario=self.jefe_compras).exists()
        )

    def test_movimiento_operario_notifica_jefe_almacen(self):
        class InvFake:
            id = 20
            lote = 'L002'

            class producto:
                nombre = 'Insulina'
                unidad_medida = 'u'

        class MovFake:
            tipo = 'salida'
            cantidad = 5
            stock_posterior = 15
            inventario = InvFake()

        notificar_movimiento_inventario(MovFake(), actor=self.operario)
        self.assertTrue(
            Notificacion.objects.filter(
                usuario=self.jefe_almacen,
                titulo='Salida de inventario registrada',
            ).exists()
        )

    def test_movimiento_jefe_almacen_no_se_auto_notifica(self):
        class InvFake:
            id = 21
            lote = 'L003'

            class producto:
                nombre = 'Aspirina'
                unidad_medida = 'u'

        class MovFake:
            tipo = 'entrada'
            cantidad = 10
            stock_posterior = 50
            inventario = InvFake()

        antes = Notificacion.objects.filter(usuario=self.jefe_almacen).count()
        notificar_movimiento_inventario(MovFake(), actor=self.jefe_almacen)
        despues = Notificacion.objects.filter(usuario=self.jefe_almacen).count()
        self.assertEqual(antes, despues)


class AlertasLoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rol_auditor, _ = Rol.objects.get_or_create(
            codigo='auditor_seguridad',
            defaults={'nombre': 'Auditor', 'activo': True},
        )
        cls.admin = User.objects.create_user(
            username='admin_sec', password='x', email='admin_sec@test.com',
            nombres='Admin', apellidos='Sec', documento='91000001',
            is_superuser=True,
        )
        cls.auditor = User.objects.create_user(
            username='auditor_sec', password='x', email='auditor_sec@test.com',
            nombres='Auditor', apellidos='Sec', documento='91000002',
        )
        UsuarioRol.objects.create(usuario=cls.auditor, rol=cls.rol_auditor)

    def test_un_fallo_no_notifica(self):
        from seguridad.models import IntentoLogin
        IntentoLogin.objects.create(
            username='victima', ip_address='10.0.0.1', exitoso=False, motivo='Credenciales inválidas',
        )
        notificar_alerta_login('victima', '10.0.0.1', 'Credenciales inválidas', max_attempts=3)
        self.assertEqual(Notificacion.objects.filter(tipo=Notificacion.Tipo.SEGURIDAD).count(), 0)

    def test_umbral_notifica_admin_y_auditor(self):
        from seguridad.models import IntentoLogin
        for _ in range(3):
            IntentoLogin.objects.create(
                username='victima2', ip_address='10.0.0.2', exitoso=False, motivo='Credenciales inválidas',
            )
        notificar_alerta_login('victima2', '10.0.0.2', 'Credenciales inválidas', max_attempts=3)
        self.assertTrue(
            Notificacion.objects.filter(usuario=self.admin, tipo=Notificacion.Tipo.SEGURIDAD).exists()
        )
        self.assertTrue(
            Notificacion.objects.filter(usuario=self.auditor, tipo=Notificacion.Tipo.SEGURIDAD).exists()
        )

    def test_bloqueo_notifica_critica(self):
        notificar_alerta_login(
            'bloqueado', '10.0.0.3', 'Cuenta bloqueada por intentos fallidos', max_attempts=3,
        )
        notif = Notificacion.objects.filter(
            usuario=self.auditor,
            prioridad=Notificacion.Prioridad.CRITICA,
        ).first()
        self.assertIsNotNone(notif)
        self.assertIn('bloqueado', notif.mensaje)
