# Title        : desktop_compras.py 
#              :
# Description  : This code defines a GUI shopping application using Tkinter and SQLite. The PurchaseApplication class 
#              : initialises the graphical interface and connects to the purchases.db database, loading seller, 
#              : customer and product data. The interface allows you to select a seller, customer and product, enter 
#              : the quantity and date, and add sale items. The application displays the price of the selected product, 
#              : updates the purchase total, and keeps a list of added items. The ‘Make Sale’ functionality records the 
#              : sale in the database, including a log record. Additionally, there is an option to check past purchases, 
#              : showing detailed sales information in a list. The application ensures that the connection to the 
#              : database is closed properly when it is finalised.
#              :
# Source       : Some inspiration from
#              : https://www.youtube.com/watch?v=bsREYrHWux0&lc=UgxRt1pAh_HHN4E0SIF4AaABAg
#              : https://docs.python.org/3/library/tk.html
#              : https://www.youtube.com/playlist?list=PLGFzROSPU9oX5a7RXGuIQR7RKV1peB2b-
# Install      :
# dependencies : The desktop_compras.py code was run on Linux, on the Ubuntu 22.04.4 LTS distribution
#              : $ sudo apt-get install python3
#              :
#              : $ sudo apt-get install python3-tk
#              : $ sudo apt-get install sqlite3 libsqlite3-dev
#              : 
# Compile and  :
# run          : $ python3 desktop_compras.py
#              :
#              :
# Directory    :
# structure    : app-store
#              : ├── api
#              : │   └── API1.py
#              : ├── data_access
#              : │   └── compras.db
#              : ├── desktop_compras.py
#              : └── keys
#              :     ├── cert.pem
#              :     |── priv.pem
#              :     └── public_key.pem
#              :
##   

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import date

class PurchaseApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("Purchase Application")

        # Connect to the SQLite database
        self.conn = sqlite3.connect('data_access/compras.db')
        self.c = self.conn.cursor()

        self.conn.commit()

        self.vendors = self.get_vendors()
        self.customers = self.get_customers()
        self.products = self.get_products()

        self.vendor_label = tk.Label(root, text="Vendor:")
        self.vendor_label.grid(row=0, column=0, padx=5, pady=5)
        self.vendor_combobox = ttk.Combobox(root, values=[vendor[1] for vendor in self.vendors])
        self.vendor_combobox.grid(row=0, column=1, padx=5, pady=5)

        self.customer_label = tk.Label(root, text="Customer:")
        self.customer_label.grid(row=1, column=0, padx=5, pady=5)
        self.customer_combobox = ttk.Combobox(root, values=[customer[1] for customer in self.customers])
        self.customer_combobox.grid(row=1, column=1, padx=5, pady=5)

        self.product_label = tk.Label(root, text="Product:")
        self.product_label.grid(row=2, column=0, padx=5, pady=5)
        self.product_combobox = ttk.Combobox(root, values=[product[1] for product in self.products])
        self.product_combobox.grid(row=2, column=1, padx=5, pady=5)

        self.price_label = tk.Label(root, text="Price:")
        self.price_label.grid(row=3, column=0, padx=5, pady=5)
        self.price_display = tk.Label(root, text="")
        self.price_display.grid(row=3, column=1, padx=5, pady=5)

        self.quantity_label = tk.Label(root, text="Quantity:")
        self.quantity_label.grid(row=4, column=0, padx=5, pady=5)
        self.quantity_entry = tk.Entry(root)
        self.quantity_entry.grid(row=4, column=1, padx=5, pady=5)

        self.date_label = tk.Label(root, text="Date:")
        self.date_label.grid(row=5, column=0, padx=5, pady=5)
        self.date_entry = tk.Entry(root)
        self.date_entry.grid(row=5, column=1, padx=5, pady=5)
        self.date_entry.insert(0, date.today().strftime("%d/%m/%Y"))  # Set the current date as default

        self.add_sale_item_button = tk.Button(root, text="Add Sale Item", command=self.add_sale_item)
        self.add_sale_item_button.grid(row=6, column=0, columnspan=2, padx=5, pady=5)

        self.make_sale_button = tk.Button(root, text="Make Sale", command=self.make_sale)
        self.make_sale_button.grid(row=7, column=0, columnspan=2, padx=5, pady=5)

        self.total_label = tk.Label(root, text="Total: R$")
        self.total_label.grid(row=8, column=0, columnspan=2, padx=5, pady=5)

        self.total_purchase = 0

        self.purchases_listbox = tk.Listbox(root)
        self.purchases_listbox.grid(row=9, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")

        # Button to check purchases
        self.check_purchases_button = tk.Button(root, text="Check Purchases", command=self.check_purchases)
        self.check_purchases_button.grid(row=10, column=0, columnspan=2, padx=5, pady=5)

        # Event to update the displayed price when a product is selected
        self.product_combobox.bind("<<ComboboxSelected>>", self.update_price)

    def get_vendors(self):
        self.c.execute("SELECT * FROM Vendedores")
        return self.c.fetchall()

    def get_customers(self):
        self.c.execute("SELECT * FROM Clientes")
        return self.c.fetchall()

    def get_products(self):
        self.c.execute("SELECT * FROM Produtos")
        return self.c.fetchall()

    def update_price(self, event):
        selected_product = self.product_combobox.get()
        for product in self.products:
            if product[1] == selected_product:
                self.price_display.config(text=f"R${product[2]:.2f}")
                break

    def add_sale_item(self):
        try:
            quantity = int(self.quantity_entry.get())
            selected_product = self.product_combobox.get()
            for product in self.products:
                if product[1] == selected_product:
                    price = product[2]
                    self.total_purchase += price * quantity
                    messagebox.showinfo("Success", "Sale item added successfully!")

                    # Update the total displayed in the GUI
                    self.total_label.config(text=f"Total: R${self.total_purchase:.2f}")

                    # Update the purchase list
                    self.load_purchases()

                    break
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid quantity.")

    def make_sale(self):
        try:
            selected_vendor = self.vendor_combobox.get()
            selected_customer = self.customer_combobox.get()
            sale_date = self.date_entry.get()

            # Get the vendor ID
            vendor_id = None
            for vendor in self.vendors:
                if vendor[1] == selected_vendor:
                    vendor_id = vendor[0]
                    break

            # Get the customer ID
            customer_id = None
            for customer in self.customers:
                if customer[1] == selected_customer:
                    customer_id = customer[0]
                    break

            # Insert sale details into the database
            self.c.execute("INSERT INTO Vendas (IDVendedor, IDCliente, Data, Total) VALUES (?, ?, ?, ?)",
                           (vendor_id, customer_id, sale_date, self.total_purchase))
            sale_id = self.c.lastrowid

            # Insert log record
            log_message = f"Venda efetuada - ID: {sale_id}, Vendedor: {selected_vendor}, Cliente: {selected_customer}, Data: {sale_date}"
            self.c.execute("INSERT INTO LogAtualizacoes (ID, Mensagem) VALUES (?, ?)", (sale_id, log_message))
            self.conn.commit()

            # Update the id_logatualizacoes field in the Vendas table
            self.c.execute("UPDATE Vendas SET id_logatualizacoes = ? WHERE id = ?", (sale_id, sale_id))
            self.conn.commit()

            # Display total sale in the GUI
            messagebox.showinfo("Sale Made", f"Sale made successfully! Total sale: R${self.total_purchase:.2f}")

            # Update the total label in the GUI
            self.total_label.config(text=f"Total: R${self.total_purchase:.2f}")

            # Reset variables for a new sale
            self.total_purchase = 0
            self.purchases_listbox.delete(0, tk.END)

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while making the sale: {e}")

    def load_purchases(self):
        # Clear the purchase list
        self.purchases_listbox.delete(0, tk.END)

        # Display the total purchase in the list
        self.purchases_listbox.insert(tk.END, f"Total Purchase: R${self.total_purchase:.2f}")

    def check_purchases(self):
        # Clear the purchase list
        self.purchases_listbox.delete(0, tk.END)

        # Query the database for detailed sales information
        self.c.execute('''SELECT Vendas.ID, Vendedores.Nome AS Vendor, Clientes.Cliente, Produtos.Produto, 
                         ItensVenda.Quantidade, ItensVenda.ValorUnitario, ItensVenda.ValorTotal, Vendas.Data
                         FROM Vendas 
                         INNER JOIN Vendedores ON Vendas.IDVendedor = Vendedores.IDVendedor 
                         INNER JOIN Clientes ON Vendas.IDCliente = Clientes.IDCliente 
                         INNER JOIN ItensVenda ON Vendas.ID = ItensVenda.IDVenda 
                         INNER JOIN Produtos ON ItensVenda.IDProduto = Produtos.IDProduto''')
        sales_data = self.c.fetchall()

        # Display the detailed sales information in the list
        for sale in sales_data:
            self.purchases_listbox.insert(tk.END, f"Sale ID: {sale[0]}, Vendor: {sale[1]}, Customer: {sale[2]}, Product: {sale[3]}, Quantity: {sale[4]}, Unit Price: R${sale[5]:.2f}, Total Price: R${sale[6]:.2f}, Date: {sale[7]}")

    def __del__(self):
        self.conn.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = PurchaseApplication(root)
    root.mainloop()

