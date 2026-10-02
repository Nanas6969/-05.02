import sys
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QLabel, QLineEdit, QComboBox,
    QDoubleSpinBox, QSpinBox, QCheckBox, QPushButton, QGroupBox,
    QMessageBox, QHeaderView
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


class MedicalApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Учет медицинских сотрудников (PyQt6)")
        self.resize(1050, 650)

        # Локальное хранилище данных
        self.employees = []
        self.next_id = 1

        self.init_ui()
        self.add_sample_data()

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

        # --- 3. Форма ввода данных ---
        form_group = QGroupBox("Управление данными сотрудника")
        form_layout = QHBoxLayout(form_group)

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
        main_layout.addWidget(form_group)

    # --- Логика работы ---

    def add_sample_data(self):
        """Добавление начальных тестовых записей"""
        samples = [
            MedicalEmployee(self.next_id, "Иванов И.И.", "Хирургия", "Хирург", "Высшая", 1.0, 85000, True),
            MedicalEmployee(self.next_id + 1, "Петрова А.С.", "Реанимация", "Анестезиолог", "Первая", 1.5, 90000, False),
        ]
        self.next_id += len(samples)
        self.employees.extend(samples)
        self.refresh_table()

    def refresh_table(self):
        """Перерисывание таблицы на основе списка сотрудников"""
        self.table.setRowCount(0)
        for emp in self.employees:
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

            # Сохраняем объект в первой ячейке строки для быстрого доступа
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, emp)

    def filter_table(self):
        """Поиск по ФИО, отделению или специальности"""
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

        emp = MedicalEmployee(
            emp_id=self.next_id,
            full_name=name,
            department=self.txt_dept.text().strip(),
            specialization=self.txt_spec.text().strip(),
            category=self.combo_cat.currentText(),
            rate=self.spin_rate.value(),
            base_salary=self.spin_salary.value(),
            is_on_shift=self.chk_shift.isChecked()
        )
        self.next_id += 1
        self.employees.append(emp)
        self.refresh_table()
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
        emp.full_name = self.txt_name.text().strip()
        emp.department = self.txt_dept.text().strip()
        emp.specialization = self.txt_spec.text().strip()
        emp.category = self.combo_cat.currentText()
        emp.rate = self.spin_rate.value()
        emp.base_salary = self.spin_salary.value()
        emp.is_on_shift = self.chk_shift.isChecked()

        self.refresh_table()

    def delete_employee(self):
        row = self.table.currentRow()
        if row < 0:
            return

        emp = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        confirm = QMessageBox.question(
            self, "Подтверждение", 
            f"Удалить сотрудника {emp.full_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.employees.remove(emp)
            self.refresh_table()
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MedicalApp()
    window.show()
    sys.argv[0] if len(sys.argv) > 0 else None
    sys.exit(app.exec())