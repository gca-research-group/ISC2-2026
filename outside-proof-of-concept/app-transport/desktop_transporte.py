##
# Title        : desktop_transporte.py 
#              :
# Description  : The desktop_transporte.py code defines a GUI application using Tkinter to schedule transport 
#              : journeys. The TransportAppGUI class initialises the graphical interface and connects to an 
#              : SQLite transporte_app.db database. The interface allows you to view lists of drivers and vehicles, 
#              : and includes fields for entering details of a journey, such as origin, destination, date/time and 
#              : value. The application allows the user to select a driver and a vehicle from the list, fill in the 
#              : journey details, and then schedule the journey, which is inserted into the database. The interface 
#              : is automatically updated after scheduling to reflect changes. In addition, error or success messages 
#              : are displayed to the user as appropriate.
#              :
# Source       : Some inspiration from
#              : https://www.youtube.com/watch?v=bsREYrHWux0&lc=UgxRt1pAh_HHN4E0SIF4AaABAg
#              : https://docs.python.org/3/library/tk.html
#              : https://www.youtube.com/playlist?list=PLGFzROSPU9oX5a7RXGuIQR7RKV1peB2b-
# Install      :
# dependencies : The desktop_transporte.py code was run on Linux, on the Ubuntu 22.04.4 LTS distribution
#              : $ sudo apt-get install python3
#              :
#              : $ sudo apt-get install python3-tk
#              : $ sudo apt-get install sqlite3 libsqlite3-dev
#              : 
# Compile and  :
# run          : $ python3 desktop_transporte.py
#              :
#              :
# Directory    :
# structure    : app-transport
#              : ├── api
#              : │   └── API2.py
#              : ├── data_access
#              : │   └── transporte_app.db
#              : ├── desktop_transporte.py
#              : └── keys
#              :     ├── cert.pem
#              :     |── priv.pem
#              :     └── public_key.pem
#              :
##   

import os
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

class TransporteAppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Transportation by App")
        
        # Get the absolute path for the database file
        db_path = os.path.abspath('data_access/transporte_app.db')
        
        # Connect to the database
        self.conn = sqlite3.connect(db_path)
        self.c = self.conn.cursor()
        
        # Create widgets
        self.label_motoristas = ttk.Label(root, text="Drivers List")
        self.tree_motoristas = ttk.Treeview(root, columns=("Nome", "CPF", "Telefone", "Status", "Avaliação Média"))
        self.label_veiculos = ttk.Label(root, text="Vehicles List")
        self.tree_veiculos = ttk.Treeview(root, columns=("Placa", "Modelo", "Disponível"))
        self.label_viagem = ttk.Label(root, text="Schedule Trip")
        self.label_origem = ttk.Label(root, text="Origin:")
        self.entry_origem = ttk.Entry(root)
        self.label_destino = ttk.Label(root, text="Destination:")
        self.entry_destino = ttk.Entry(root)
        self.label_data_hora = ttk.Label(root, text="Date/Time (YYYY-MM-DD HH:MM):")
        self.entry_data_hora = ttk.Entry(root)
        self.label_valor = ttk.Label(root, text="Value:")
        self.entry_valor = ttk.Entry(root)
        self.btn_agendar_viagem = ttk.Button(root, text="Schedule Trip", command=self.agendar_viagem)

        # Configure drivers list columns
        self.tree_motoristas.heading("#0", text="ID")
        self.tree_motoristas.heading("Nome", text="Name")
        self.tree_motoristas.heading("CPF", text="CPF")
        self.tree_motoristas.heading("Telefone", text="Phone")
        self.tree_motoristas.heading("Status", text="Status")
        self.tree_motoristas.heading("Avaliação Média", text="Average Rating")

        # Configure vehicles list columns
        self.tree_veiculos.heading("#0", text="ID")
        self.tree_veiculos.heading("Placa", text="License Plate")
        self.tree_veiculos.heading("Modelo", text="Model")
        self.tree_veiculos.heading("Disponível", text="Available")

        # Add data to the trees
        self.carregar_motoristas()
        self.carregar_veiculos()

        # Layout widgets
        self.label_motoristas.grid(row=0, column=0, columnspan=2, sticky="w")
        self.tree_motoristas.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.label_veiculos.grid(row=2, column=0, columnspan=2, sticky="w")
        self.tree_veiculos.grid(row=3, column=0, columnspan=2, sticky="nsew")
        self.label_viagem.grid(row=4, column=0, columnspan=2, sticky="w")
        self.label_origem.grid(row=5, column=0, sticky="w")
        self.entry_origem.grid(row=5, column=1, sticky="w")
        self.label_destino.grid(row=6, column=0, sticky="w")
        self.entry_destino.grid(row=6, column=1, sticky="w")
        self.label_data_hora.grid(row=7, column=0, sticky="w")
        self.entry_data_hora.grid(row=7, column=1, sticky="w")
        self.label_valor.grid(row=8, column=0, sticky="w")
        self.entry_valor.grid(row=8, column=1, sticky="w")
        self.btn_agendar_viagem.grid(row=9, column=0, columnspan=2)

    def carregar_motoristas(self):
        # Clear tree
        for record in self.tree_motoristas.get_children():
            self.tree_motoristas.delete(record)

        # Query drivers from the database
        self.c.execute("SELECT * FROM Motoristas")
        motoristas = self.c.fetchall()

        # Populate the tree with driver data
        for motorista in motoristas:
            self.tree_motoristas.insert("", "end", text=motorista[0], values=(motorista[1], motorista[2], motorista[3], motorista[6], motorista[7]))

    def carregar_veiculos(self):
        # Clear tree
        for record in self.tree_veiculos.get_children():
            self.tree_veiculos.delete(record)

        # Query vehicles from the database
        self.c.execute("SELECT * FROM Veiculos")
        veiculos = self.c.fetchall()

        # Populate the tree with vehicle data
        for veiculo in veiculos:
            disponibilidade = "Yes" if veiculo[3] == 1 else "No"
            self.tree_veiculos.insert("", "end", text=veiculo[0], values=(veiculo[1], veiculo[2], disponibilidade))

    def agendar_viagem(self):
        # Get the values entered by the user
        origem = self.entry_origem.get()
        destino = self.entry_destino.get()
        data_hora = self.entry_data_hora.get()
        valor = self.entry_valor.get()

        # Check if all fields are filled
        if not (origem and destino and data_hora and valor):
            messagebox.showerror("Error", "Please fill in all fields.")
            return

        try:
            valor = float(valor)
        except ValueError:
            messagebox.showerror("Error", "The trip value must be a number.")
            return

        # Check if a driver is selected
        if not self.tree_motoristas.selection():
            messagebox.showerror("Error", "Please select a driver.")
            return

        # Check if a vehicle is selected
        if not self.tree_veiculos.selection():
            messagebox.showerror("Error", "Please select a vehicle.")
            return

        # Get the selected driver ID
        id_motorista = int(self.tree_motoristas.item(self.tree_motoristas.selection())['text'])

        # Get the selected vehicle ID
        id_veiculo = int(self.tree_veiculos.item(self.tree_veiculos.selection())['text'])

        # Insert the trip into the database
        self.c.execute("INSERT INTO Viagens (id_motorista, id_veiculo, data_hora_inicio, local_origem, local_destino, valor) VALUES (?, ?, ?, ?, ?, ?)",
                       (id_motorista, id_veiculo, data_hora, origem, destino, valor))
        self.conn.commit()

        # Update the driver and vehicle trees
        self.carregar_motoristas()
        self.carregar_veiculos()

        # Display success message
        messagebox.showinfo("Success", "Trip successfully scheduled!")

if __name__ == "__main__":
    # Create and configure the main window
    root = tk.Tk()
    app = TransporteAppGUI(root)
    root.mainloop()

