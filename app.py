import sys
import sqlite3
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QLabel, QLineEdit, QComboBox,
    QDoubleSpinBox, QSpinBox, QCheckBox, QPushButton, QGroupBox,
    QMessageBox, QHeaderView, QDialog, QFormLayout
)
from PyQt6.QtCore import Qt


class MedicalEmployee:
    """Модель медицинского сотрудника"""
    def __init__(self, emp_id, full_name, department, specialization, 
                 category, rate, base_salary, is_on_shift=False, expiry_date=None):
        self.id = emp_id
        self.full_name = full_name
        self.department = department
        self.specialization = specialization
        self.category = category  # Высшая, Первая, Вторая, Без категории
        self.rate = rate          # 0.5, 1.0, 1.5
        self.base_salary = base_salary
        self.is_on_shift = is_on_shift
        self.expiry_date = expiry_date or (datetime.now() + timedelta(days=1825)).strftime("%Y-%m-%d")

    @property
    def calculated_salary(self):
        """Расчет итоговой зарплаты с учетом категории и ставки"""
        category_bonuses = {
            "Высшая": 1.3,
            "Первая": 1.2,
            "Вторая": 1.1,
            "Без категории": 1.0
        }
        bonus = category_bonuses.get(self.category, 1.0)
        return self.base_salary * self.rate * bonus


class LoginDialog(QDialog):
    """Окно авторизации"""
    def __init__(self, cursor, conn):
        super().__init__()
        self.cursor = cursor
        self.conn = conn
        self.user_role = None
        self.username = None

        self.setWindowTitle("Авторизация в системе")
        self.resize(300, 150)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        self.txt_login = QLineEdit()
        self.txt_pass = QLineEdit()
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)

        layout.addRow("Логин:", self.txt_login)
        layout.addRow("Пароль:", self.txt_pass)

        btn_login = QPushButton("Войти")
        btn_login.clicked.connect(self.handle_login)
        layout.addRow(btn_login)

        # Подсказка для теста
        lbl_hint = QLabel("<small>Админ: admin / admin<br>Пользователь: doctor / 12345</small>")
        layout.addRow(lbl_hint)

    def handle_login(self):
        login = self.txt_login.text().strip()
        password = self.txt_pass.text().strip()

        if not login or not password:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля!")
            return

        self.cursor.execute("SELECT role FROM users WHERE username = ? AND password = ?", (login, password))
        result = self.cursor.fetchone()

        if result:
            self.user_role = result[0]
            self.username = login
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", "Неверный логин или пароль!")


class MedicalApp(QMainWindow):
    def __init__(self, username, role, conn, cursor):
        super().__init__()
        self.username = username
        self.role = role  # 'admin' или 'user'
        self.conn = conn
        self.cursor = cursor
        
        role_title = "Администратор" if role == 'admin' else "Сотрудник"
        self.setWindowTitle(f"Учет медицинских сотрудников | Пользователь: {self.username} ({role_title})")
        self.resize(1050, 650)

        self.init_ui()
        self.load_employees()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # --- 1. Панель поиска ---
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Поиск (ФИО / Отделение / Специальность):"))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Введите текст для фильтрации...")
        self.txt_search.textChanged.connect(self.filter_table)
        search_layout.addWidget(self.txt_search)
        main_layout.addLayout(search_layout)

        # --- 2. Таблица сотрудников ---
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "ФИО Врача", "Отделение", "Специализация", 
            "Категория", "Ставка", "Оклад", "Итого с коэф.", "На смене"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.selectionModel().selectionChanged.connect(self.on_row_selected)
        main_layout.addWidget(self.table)

        # --- 3. Форма ввода данных (доступна только админу) ---
        self.form_group = QGroupBox("Управление данными сотрудника")
        form_layout = QHBoxLayout(self.form_group)

        # Левая колонка формы
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("ФИО:"))
        self.txt_name = QLineEdit()
        col1.addWidget(self.txt_name)

        col1.addWidget(QLabel("Отделение:"))
        self.txt_dept = QLineEdit()
        col1.addWidget(self.txt_dept)

        col1.addWidget(QLabel("Специализация:"))
        self.txt_spec = QLineEdit()
        col1.addWidget(self.txt_spec)

        # Средняя колонка формы
        col2 = QVBoxLayout()
        col2.addWidget(QLabel("Категория:"))
        self.combo_cat = QComboBox()
        self.combo_cat.addItems(["Без категории", "Вторая", "Первая", "Высшая"])
        col2.addWidget(self.combo_cat)

        col2.addWidget(QLabel("Ставка:"))
        self.spin_rate = QDoubleSpinBox()
        self.spin_rate.setRange(0.25, 2.0)
        self.spin_rate.setSingleStep(0.25)
        self.spin_rate.setValue(1.0)
        col2.addWidget(self.spin_rate)

        col2.addWidget(QLabel("Базовый оклад (руб):"))
        self.spin_salary = QSpinBox()
        self.spin_salary.setRange(0, 1000000)
        self.spin_salary.setSingleStep(5000)
        self.spin_salary.setValue(60000)
        col2.addWidget(self.spin_salary)

        # Правая колонка — статус и кнопки
        col3 = QVBoxLayout()
        self.chk_shift = QCheckBox("На дежурстве (Смена)")
        col3.addWidget(self.chk_shift)

        btn_add = QPushButton("Добавить")
        btn_add.clicked.connect(self.add_employee)
        col3.addWidget(btn_add)

        btn_update = QPushButton("Сохранить изменения")
        btn_update.clicked.connect(self.update_employee)
        col3.addWidget(btn_update)

        btn_delete = QPushButton("Удалить")
        btn_delete.clicked.connect(self.delete_employee)
        col3.addWidget(btn_delete)

        btn_clear = QPushButton("Очистить форму")
        btn_clear.clicked.connect(self.clear_form)
        col3.addWidget(btn_clear)

        form_layout.addLayout(col1)
        form_layout.addLayout(col2)
        form_layout.addLayout(col3)
        main_layout.addWidget(self.form_group)

        # Если зашел обычный пользователь, скрываем панель управления
        if self.role != 'admin':
            self.form_group.setEnabled(False)
            self.form_group.setTitle("Управление данными сотрудника (Доступно только администратору)")

    def load_employees(self):
        """Загрузка данных из БД в таблицу"""
        self.cursor.execute("SELECT id, full_name, department, specialization, category, rate, base_salary, is_on_shift, expiry_date FROM employees")
        rows = self.cursor.fetchall()
        self.refresh_table_from_rows(rows)

    def refresh_table_from_rows(self, rows):
        self.table.setRowCount(0)
        for row_data in rows:
            emp_id, full_name, dept, spec, cat, rate, salary, is_shift, expiry = row_data
            emp = MedicalEmployee(
                emp_id=emp_id, full_name=full_name, department=dept,
                specialization=spec, category=cat, rate=rate,
                base_salary=salary, is_on_shift=bool(is_shift), expiry_date=expiry
            )

            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(str(emp.id)))
            self.table.setItem(row, 1, QTableWidgetItem(emp.full_name))
            self.table.setItem(row, 2, QTableWidgetItem(emp.department))
            self.table.setItem(row, 3, QTableWidgetItem(emp.specialization))
            self.table.setItem(row, 4, QTableWidgetItem(emp.category))
            self.table.setItem(row, 5, QTableWidgetItem(str(emp.rate)))
            self.table.setItem(row, 6, QTableWidgetItem(f"{emp.base_salary:,.2f} руб."))
            self.table.setItem(row, 7, QTableWidgetItem(f"{emp.calculated_salary:,.2f} руб."))
            self.table.setItem(row, 8, QTableWidgetItem("Да" if emp.is_on_shift else "Нет"))

            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, emp)

    def filter_table(self):
        query = self.txt_search.text().lower()
        for row in range(self.table.rowCount()):
            emp = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            match = (
                query in emp.full_name.lower() or
                query in emp.department.lower() or
                query in emp.specialization.lower()
            )
            self.table.setRowHidden(row, not match)

    def add_employee(self):
        name = self.txt_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите ФИО сотрудника!")
            return

        self.cursor.execute("""
            INSERT INTO employees (full_name, department, specialization, category, rate, base_salary, is_on_shift, expiry_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name, self.txt_dept.text().strip(), self.txt_spec.text().strip(),
            self.combo_cat.currentText(), self.spin_rate.value(), self.spin_salary.value(),
            1 if self.chk_shift.isChecked() else 0,
            (datetime.now() + timedelta(days=1825)).strftime("%Y-%m-%d")
        ))
        self.conn.commit()
        self.load_employees()
        self.clear_form()

    def on_row_selected(self):
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return

        row = self.table.currentRow()
        emp = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        self.txt_name.setText(emp.full_name)
        self.txt_dept.setText(emp.department)
        self.txt_spec.setText(emp.specialization)
        self.combo_cat.setCurrentText(emp.category)
        self.spin_rate.setValue(emp.rate)
        self.spin_salary.setValue(int(emp.base_salary))
        self.chk_shift.setChecked(emp.is_on_shift)

    def update_employee(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Внимание", "Выберите сотрудника из таблицы!")
            return

        emp = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.cursor.execute("""
            UPDATE employees 
            SET full_name = ?, department = ?, specialization = ?, category = ?, rate = ?, base_salary = ?, is_on_shift = ?
            WHERE id = ?
        """, (
            self.txt_name.text().strip(), self.txt_dept.text().strip(), self.txt_spec.text().strip(),
            self.combo_cat.currentText(), self.spin_rate.value(), self.spin_salary.value(),
            1 if self.chk_shift.isChecked() else 0, emp.id
        ))
        self.conn.commit()
        self.load_employees()

    def delete_employee(self):
        row = self.table.currentRow()
        if row < 0:
            return

        emp = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        confirm = QMessageBox.question(
            self, "Подтверждение", f"Удалить сотрудника {emp.full_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.cursor.execute("DELETE FROM employees WHERE id = ?", (emp.id,))
            self.conn.commit()
            self.load_employees()
            self.clear_form()

    def clear_form(self):
        self.txt_name.clear()
        self.txt_dept.clear()
        self.txt_spec.clear()
        self.combo_cat.setCurrentIndex(0)
        self.spin_rate.setValue(1.0)
        self.spin_salary.setValue(60000)
        self.chk_shift.setChecked(False)
        self.table.clearSelection()

    def closeEvent(self, event):
        """Закрываем соединение с базой при выходе из главного окна"""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
        event.accept()


def init_database():
    """Инициализация базы данных, таблиц и дефолтных записей"""
    conn = sqlite3.connect("medical_staff.db")
    cursor = conn.cursor()

    # Таблица сотрудников
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            department TEXT,
            specialization TEXT,
            category TEXT,
            rate REAL,
            base_salary REAL,
            is_on_shift INTEGER,
            expiry_date TEXT
        )
    """)

    # Таблица пользователей для авторизации
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # Создадим дефолтного администратора и пользователя, если таблица пуста
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("admin", "admin", "admin"))
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("doctor", "12345", "user"))
        conn.commit()

    # Добавим тестовых сотрудников, если таблица пуста
    cursor.execute("SELECT COUNT(*) FROM employees")
    if cursor.fetchone()[0] == 0:
        samples = [
            ("Иванов И.И.", "Хирургия", "Хирург", "Высшая", 1.0, 85000, 1, None),
            ("Петрова А.С.", "Реанимация", "Анестезиолог", "Первая", 1.5, 90000, 0, None),
        ]
        cursor.executemany("""
            INSERT INTO employees (full_name, department, specialization, category, rate, base_salary, is_on_shift, expiry_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, samples)
        conn.commit()

    return conn, cursor


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Инициализируем БД
    conn, cursor = init_database()

    # Показываем окно авторизации
    login_dialog = LoginDialog(cursor, conn)
    if login_dialog.exec() == QDialog.DialogCode.Accepted:
        # Если вошли успешно, передаем коннект и курсор внутрь главного окна через аргументы
        window = MedicalApp(login_dialog.username, login_dialog.user_role, conn, cursor)
        window.show()
        
        exit_code = app.exec()
        sys.exit(exit_code)
    else:
        conn.close()
        sys.exit(0)