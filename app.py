import sys
import serial
import threading
import time
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import serial.tools.list_ports
from queue import Queue

class SerialWorker:
    """Serial işlemleri için worker class"""
    def __init__(self, data_callback, status_callback):
        self.virtual_serial = None
        self.physical_serial = None
        self.running = False
        self.data_callback = data_callback
        self.status_callback = status_callback
        
    def connect_ports(self, virtual_port, physical_port, baudrate):
        """Portlara bağlan"""
        try:
            self.virtual_serial = serial.Serial(
                port=virtual_port,
                baudrate=baudrate,
                timeout=0.1,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            
            self.physical_serial = serial.Serial(
                port=physical_port,
                baudrate=baudrate,
                timeout=0.1,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            
            self.status_callback(True, "Bağlantı başarılı!")
            return True
            
        except Exception as e:
            self.status_callback(False, f"Bağlantı hatası: {str(e)}")
            return False
    
    def start_monitoring(self):
        """Monitoring başlat"""
        self.running = True
        
        # İki thread başlat
        self.t1 = threading.Thread(target=self.virtual_to_physical, daemon=True)
        self.t2 = threading.Thread(target=self.physical_to_virtual, daemon=True)
        
        self.t1.start()
        self.t2.start()
    
    def stop_monitoring(self):
        """Monitoring durdur"""
        self.running = False
        
        if self.virtual_serial and self.virtual_serial.is_open:
            self.virtual_serial.close()
        if self.physical_serial and self.physical_serial.is_open:
            self.physical_serial.close()
    
    def virtual_to_physical(self):
        """Sanal -> Fiziksel port thread"""
        while self.running:
            try:
                if self.virtual_serial and self.virtual_serial.is_open:
                    if self.virtual_serial.in_waiting > 0:
                        data = self.virtual_serial.read(self.virtual_serial.in_waiting)
                        if data:
                            self.data_callback(data, "TO_DEVICE")
                            if self.physical_serial and self.physical_serial.is_open:
                                self.physical_serial.write(data)
                                self.physical_serial.flush()
                time.sleep(0.001)
            except Exception as e:
                if self.running:
                    self.status_callback(False, f"V->P Hata: {str(e)}")
                break
    
    def physical_to_virtual(self):
        """Fiziksel -> Sanal port thread"""
        while self.running:
            try:
                if self.physical_serial and self.physical_serial.is_open:
                    if self.physical_serial.in_waiting > 0:
                        data = self.physical_serial.read(self.physical_serial.in_waiting)
                        if data:
                            self.data_callback(data, "FROM_DEVICE")
                            if self.virtual_serial and self.virtual_serial.is_open:
                                self.virtual_serial.write(data)
                                self.virtual_serial.flush()
                time.sleep(0.001)
            except Exception as e:
                if self.running:
                    self.status_callback(False, f"P->V Hata: {str(e)}")
                break

class SerialSnifferGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.worker = SerialWorker(self.handle_data, self.handle_connection_status)
        self.stats = {
            'bytes_to_device': 0,
            'bytes_from_device': 0,
            'packets_to_device': 0,
            'packets_from_device': 0,
            'start_time': None
        }
        
        # Thread-safe queue for GUI updates
        self.gui_queue = Queue()
        
        self.init_ui()
        self.setup_timer()
        
    def init_ui(self):
        """UI'yi başlat"""
        self.root.title("USB/Serial Sniffer v1.0 - Tkinter Edition")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f0f0f0')
        
        # Ana frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Kontrol paneli
        self.create_control_panel(main_frame)
        
        # Veri görüntüleme alanı
        self.create_data_area(main_frame)
        
        # Durum çubuğu
        self.create_status_bar()
        
        # Menü çubuğu
        self.create_menu_bar()
        
        # İlk port listesini yükle
        self.refresh_ports()
        
    def create_control_panel(self, parent):
        """Kontrol paneli oluştur"""
        control_frame = ttk.LabelFrame(parent, text="🔧 Bağlantı Ayarları", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # İlk satır
        row1 = ttk.Frame(control_frame)
        row1.pack(fill=tk.X, pady=(0, 10))
        
        # Sanal port seçimi
        ttk.Label(row1, text="Sanal Port:").pack(side=tk.LEFT, padx=(0, 5))
        self.virtual_port_var = tk.StringVar()
        self.virtual_port_combo = ttk.Combobox(row1, textvariable=self.virtual_port_var, width=20, state="readonly")
        self.virtual_port_combo.pack(side=tk.LEFT, padx=(0, 20))
        
        # Fiziksel port seçimi
        ttk.Label(row1, text="Fiziksel Port:").pack(side=tk.LEFT, padx=(0, 5))
        self.physical_port_var = tk.StringVar()
        self.physical_port_combo = ttk.Combobox(row1, textvariable=self.physical_port_var, width=30, state="readonly")
        self.physical_port_combo.pack(side=tk.LEFT, padx=(0, 20))
        
        # Baud rate
        ttk.Label(row1, text="Baud Rate:").pack(side=tk.LEFT, padx=(0, 5))
        self.baudrate_var = tk.StringVar(value="9600")
        self.baudrate_combo = ttk.Combobox(row1, textvariable=self.baudrate_var, width=10, state="readonly")
        self.baudrate_combo['values'] = ("9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600")
        self.baudrate_combo.pack(side=tk.LEFT, padx=(0, 20))
        
        # Portları yenile butonu
        self.refresh_btn = ttk.Button(row1, text="🔄 Yenile", command=self.refresh_ports)
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # İkinci satır - Kontrol butonları
        row2 = ttk.Frame(control_frame)
        row2.pack(fill=tk.X)
        
        # Başlat butonu
        self.start_btn = ttk.Button(row2, text="▶ Başlat", command=self.start_sniffing)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Durdur butonu
        self.stop_btn = ttk.Button(row2, text="⏹ Durdur", command=self.stop_sniffing, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Temizle butonu
        self.clear_btn = ttk.Button(row2, text="🗑 Temizle", command=self.clear_data)
        self.clear_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Kaydet butonu
        self.save_btn = ttk.Button(row2, text="💾 Kaydet", command=self.save_log)
        self.save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # İstatistikler
        self.stats_label = ttk.Label(row2, text="📊 İstatistikler: Hazır", foreground="blue")
        self.stats_label.pack(side=tk.RIGHT, padx=(10, 0))
    
    def create_data_area(self, parent):
        """Veri görüntüleme alanı oluştur"""
        # Ana notebook (tab container)
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Ayrı Paneller
        split_frame = ttk.Frame(notebook)
        notebook.add(split_frame, text="📱 Ayrı Paneller")
        
        # PanedWindow ile bölünebilir alan
        paned = ttk.PanedWindow(split_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Sol panel - Giden veriler
        left_frame = ttk.LabelFrame(paned, text="📤 Cihaza Giden Veriler (Uygulama → Cihaz)", padding="5")
        self.to_device_text = scrolledtext.ScrolledText(
            left_frame, 
            font=("Consolas", 9), 
            bg="#2b2b2b", 
            fg="#ff6b6b",
            insertbackground="white",
            wrap=tk.NONE,
            state=tk.DISABLED
        )
        self.to_device_text.pack(fill=tk.BOTH, expand=True)
        paned.add(left_frame, weight=1)
        
        # Sağ panel - Gelen veriler
        right_frame = ttk.LabelFrame(paned, text="📥 Cihazdan Gelen Veriler (Cihaz → Uygulama)", padding="5")
        self.from_device_text = scrolledtext.ScrolledText(
            right_frame, 
            font=("Consolas", 9), 
            bg="#2b2b2b", 
            fg="#4ecdc4",
            insertbackground="white",
            wrap=tk.NONE,
            state=tk.DISABLED
        )
        self.from_device_text.pack(fill=tk.BOTH, expand=True)
        paned.add(right_frame, weight=1)
        
        # Tab 2: Birleşik Görünüm
        combined_frame = ttk.Frame(notebook)
        notebook.add(combined_frame, text="📊 Birleşik Görünüm")
        
        combined_label_frame = ttk.LabelFrame(combined_frame, text="🔄 Tüm Veri Akışı (Zaman Sıralı)", padding="5")
        combined_label_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.all_data_text = scrolledtext.ScrolledText(
            combined_label_frame,
            font=("Consolas", 9),
            bg="#2b2b2b",
            fg="#ffffff",
            insertbackground="white",
            wrap=tk.NONE,
            state=tk.DISABLED
        )
        self.all_data_text.pack(fill=tk.BOTH, expand=True)
        
        # Tab 3: Raw Hex View
        hex_frame = ttk.Frame(notebook)
        notebook.add(hex_frame, text="🔍 Raw Hex")
        
        hex_label_frame = ttk.LabelFrame(hex_frame, text="⚡ Raw Hex Dump", padding="5")
        hex_label_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.hex_text = scrolledtext.ScrolledText(
            hex_label_frame,
            font=("Consolas", 9),
            bg="#1a1a1a",
            fg="#00ff00",
            insertbackground="white",
            wrap=tk.NONE,
            state=tk.DISABLED
        )
        self.hex_text.pack(fill=tk.BOTH, expand=True)
    
    def create_status_bar(self):
        """Durum çubuğu oluştur"""
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = ttk.Label(
            self.status_frame, 
            text="🟡 Hazır - Portları seçin ve Başlat'a tıklayın",
            relief=tk.SUNKEN,
            padding="5"
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def create_menu_bar(self):
        """Menü çubuğu oluştur"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Dosya menüsü
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Dosya", menu=file_menu)
        file_menu.add_command(label="💾 Kaydet...", command=self.save_log, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="🚪 Çıkış", command=self.root.quit, accelerator="Alt+F4")
        
        # Görünüm menüsü
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Görünüm", menu=view_menu)
        view_menu.add_command(label="🗑 Tümünü Temizle", command=self.clear_data, accelerator="Ctrl+L")
        view_menu.add_command(label="🔄 Portları Yenile", command=self.refresh_ports, accelerator="F5")
        
        # Araçlar menüsü
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Araçlar", menu=tools_menu)
        tools_menu.add_command(label="📊 İstatistikleri Göster", command=self.show_detailed_stats)
        tools_menu.add_command(label="🔍 Port Tarayıcısı", command=self.show_port_scanner)
        
        # Yardım menüsü
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Yardım", menu=help_menu)
        help_menu.add_command(label="ℹ Hakkında", command=self.show_about)
        help_menu.add_command(label="❓ Kullanım Kılavuzu", command=self.show_help)
        
        # Klavye kısayolları
        self.root.bind('<Control-s>', lambda e: self.save_log())
        self.root.bind('<Control-l>', lambda e: self.clear_data())
        self.root.bind('<F5>', lambda e: self.refresh_ports())
    
    def get_available_ports(self):
        """Tüm mevcut COM portlarını listele"""
        ports = []
        try:
            available_ports = serial.tools.list_ports.comports()
            for port in available_ports:
                port_info = f"{port.device}"
                if port.description and port.description != "n/a":
                    port_info += f" - {port.description}"
                if port.manufacturer and port.manufacturer != "n/a":
                    port_info += f" ({port.manufacturer})"
                ports.append(port_info)
        except Exception as e:
            print(f"Port tarama hatası: {e}")
        
        return ports
    
    def refresh_ports(self):
        """Mevcut COM portlarını yenile"""
        try:
            ports = self.get_available_ports()
            
            # Sanal portlar için hem fiziksel portları hem de com0com portlarını göster
            self.virtual_port_combo['values'] = ports
            self.physical_port_combo['values'] = ports
            
            # Mevcut seçimleri koru
            current_virtual = self.virtual_port_var.get()
            current_physical = self.physical_port_var.get()
            
            # Eğer seçili portlar hala mevcutsa koru
            if current_virtual and any(current_virtual.split(' -')[0] in port for port in ports):
                pass  # Mevcut seçimi koru
            elif ports:
                # COM4'ü varsayılan olarak seç (sanal port için)
                com4_port = next((port for port in ports if "COM4" in port), None)
                if com4_port:
                    self.virtual_port_var.set(com4_port)
            
            if current_physical and any(current_physical.split(' -')[0] in port for port in ports):
                pass  # Mevcut seçimi koru
            elif ports:
                # İlk portu fiziksel port olarak seç
                self.physical_port_var.set(ports[0] if ports else "")
            
            port_count = len(ports)
            self.update_status(f"🔄 {port_count} port bulundu ve listelendi")
            
        except Exception as e:
            self.update_status(f"❌ Port yenileme hatası: {str(e)}")
    
    def start_sniffing(self):
        """Sniffing başlat"""
        virtual_port = self.virtual_port_var.get().split(' - ')[0] if ' - ' in self.virtual_port_var.get() else self.virtual_port_var.get()
        physical_port = self.physical_port_var.get().split(' - ')[0] if ' - ' in self.physical_port_var.get() else self.physical_port_var.get()
        
        if not virtual_port or not physical_port:
            messagebox.showerror("Hata", "Lütfen hem sanal hem de fiziksel port seçin!")
            return
        
        if virtual_port == physical_port:
            messagebox.showerror("Hata", "Sanal port ve fiziksel port aynı olamaz!")
            return
        
        try:
            baudrate = int(self.baudrate_var.get())
        except ValueError:
            messagebox.showerror("Hata", "Geçerli bir baud rate girin!")
            return
        
        if self.worker.connect_ports(virtual_port, physical_port, baudrate):
            self.worker.start_monitoring()
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.stats['start_time'] = time.time()
            self.update_status(f"✅ Sniffing aktif: {virtual_port} ↔ {physical_port} @ {baudrate} baud")
    
    def stop_sniffing(self):
        """Sniffing durdur"""
        self.worker.stop_monitoring()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.update_status("⏹ Sniffing durduruldu")
    
    def handle_data(self, data, direction):
        """Gelen veriyi işle"""
        # Thread-safe GUI güncellemesi için queue kullan
        self.gui_queue.put(('data', data, direction))
    
    def handle_connection_status(self, success, message):
        """Bağlantı durumu işle"""
        self.gui_queue.put(('status', success, message))
    
    def process_gui_queue(self):
        """GUI queue'sunu işle"""
        try:
            while not self.gui_queue.empty():
                item = self.gui_queue.get_nowait()
                
                if item[0] == 'data':
                    self.display_data(item[1], item[2])
                elif item[0] == 'status':
                    self.display_connection_status(item[1], item[2])
                    
        except Exception as e:
            print(f"GUI queue işleme hatası: {e}")
    
    def display_data(self, data, direction):
        """Veriyi GUI'de göster"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        hex_str = ' '.join(f'{b:02X}' for b in data)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
        
        if direction == "TO_DEVICE":
            arrow = ">>>"
            self.stats['bytes_to_device'] += len(data)
            self.stats['packets_to_device'] += 1
            target_text = self.to_device_text
        else:
            arrow = "<<<"
            self.stats['bytes_from_device'] += len(data)
            self.stats['packets_from_device'] += 1
            target_text = self.from_device_text
        
        # Formatlanmış metin
        log_entry = f"[{timestamp}] {arrow} ({len(data)} bytes)\nHEX: {hex_str}\nASC: {ascii_str}\n{'-'*60}\n"
        
        # Ayrı panellere ekle
        target_text.config(state=tk.NORMAL)
        target_text.insert(tk.END, log_entry)
        target_text.see(tk.END)
        target_text.config(state=tk.DISABLED)
        
        # Birleşik görünüme ekle
        combined_entry = f"[{timestamp}] {arrow} {hex_str} | {ascii_str}\n"
        self.all_data_text.config(state=tk.NORMAL)
        if direction == "TO_DEVICE":
            self.all_data_text.insert(tk.END, combined_entry, "to_device")
        else:
            self.all_data_text.insert(tk.END, combined_entry, "from_device")
        self.all_data_text.see(tk.END)
        self.all_data_text.config(state=tk.DISABLED)
        
        # Raw hex görünümüne ekle
        hex_entry = f"[{timestamp}] {arrow} {hex_str}\n"
        self.hex_text.config(state=tk.NORMAL)
        self.hex_text.insert(tk.END, hex_entry)
        self.hex_text.see(tk.END)
        self.hex_text.config(state=tk.DISABLED)
        
        # Renk etiketlerini ayarla
        self.all_data_text.tag_config("to_device", foreground="#ff6b6b")
        self.all_data_text.tag_config("from_device", foreground="#4ecdc4")
    
    def display_connection_status(self, success, message):
        """Bağlantı durumunu göster"""
        if success:
            self.update_status(f"✅ {message}")
        else:
            self.update_status(f"❌ {message}")
            messagebox.showerror("Bağlantı Hatası", message)
            self.stop_sniffing()
    
    def update_status(self, message):
        """Durum çubuğunu güncelle"""
        self.status_label.config(text=message)
    
    def update_stats(self):
        """İstatistikleri güncelle"""
        if self.stats['start_time']:
            elapsed = time.time() - self.stats['start_time']
            total_bytes = self.stats['bytes_to_device'] + self.stats['bytes_from_device']
            total_packets = self.stats['packets_to_device'] + self.stats['packets_from_device']
            
            stats_text = (f"📊 Süre: {elapsed:.0f}s | "
                         f"📤: {self.stats['bytes_to_device']}B/{self.stats['packets_to_device']}P | "
                         f"📥: {self.stats['bytes_from_device']}B/{self.stats['packets_from_device']}P | "
                         f"Toplam: {total_bytes}B/{total_packets}P")
            
            self.stats_label.config(text=stats_text)
        else:
            self.stats_label.config(text="📊 İstatistikler: Hazır")
    
    def clear_data(self):
        """Tüm veriyi temizle"""
        for text_widget in [self.to_device_text, self.from_device_text, self.all_data_text, self.hex_text]:
            text_widget.config(state=tk.NORMAL)
            text_widget.delete(1.0, tk.END)
            text_widget.config(state=tk.DISABLED)
        
        # İstatistikleri sıfırla (sadece sayıları, zamanı koru)
        if not self.stats['start_time']:  # Eğer çalışmıyorsa tamamen sıfırla
            self.stats = {
                'bytes_to_device': 0,
                'bytes_from_device': 0,
                'packets_to_device': 0,
                'packets_from_device': 0,
                'start_time': None
            }
        else:  # Çalışıyorsa sadece sayıları sıfırla
            self.stats.update({
                'bytes_to_device': 0,
                'bytes_from_device': 0,
                'packets_to_device': 0,
                'packets_from_device': 0
            })
    
    def save_log(self):
        """Log'u dosyaya kaydet"""
        filename = filedialog.asksaveasfilename(
            title="Log Dosyası Kaydet",
            defaultextension=".txt",
            initialname=f"sniffer_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("=== USB/Serial Sniffer Log ===\n")
                    f.write(f"Tarih: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    
                    f.write("GIDEN VERİLER (Uygulama → Cihaz):\n")
                    f.write("=" * 50 + "\n")
                    f.write(self.to_device_text.get(1.0, tk.END))
                    
                    f.write("\n\nGELEN VERİLER (Cihaz → Uygulama):\n")
                    f.write("=" * 50 + "\n")
                    f.write(self.from_device_text.get(1.0, tk.END))
                    
                    f.write("\n\nTÜM VERİ AKIŞI:\n")
                    f.write("=" * 50 + "\n")
                    f.write(self.all_data_text.get(1.0, tk.END))
                    
                    f.write("\n\nRAW HEX DUMP:\n")
                    f.write("=" * 50 + "\n")
                    f.write(self.hex_text.get(1.0, tk.END))
                
                messagebox.showinfo("Başarılı", f"Log dosyası kaydedildi:\n{filename}")
                
            except Exception as e:
                messagebox.showerror("Hata", f"Dosya kaydedilemedi:\n{str(e)}")
    
    def show_detailed_stats(self):
        """Detaylı istatistikleri göster"""
        if self.stats['start_time']:
            elapsed = time.time() - self.stats['start_time']
            total_bytes = self.stats['bytes_to_device'] + self.stats['bytes_from_device']
            total_packets = self.stats['packets_to_device'] + self.stats['packets_from_device']
            
            avg_packet_size = total_bytes / total_packets if total_packets > 0 else 0
            throughput = total_bytes / elapsed if elapsed > 0 else 0
            
            stats_text = f"""📊 Detaylı İstatistikler:

⏱ Çalışma Süresi: {elapsed:.1f} saniye
📤 Cihaza Gönderilen: {self.stats['bytes_to_device']} byte, {self.stats['packets_to_device']} paket
📥 Cihazdan Alınan: {self.stats['bytes_from_device']} byte, {self.stats['packets_from_device']} paket
📊 Toplam: {total_bytes} byte, {total_packets} paket
📏 Ortalama Paket Boyutu: {avg_packet_size:.1f} byte
⚡ Ortalama Throughput: {throughput:.1f} byte/saniye

🔄 Veri Yönü Dağılımı:
   Giden: %{(self.stats['bytes_to_device']/total_bytes*100 if total_bytes > 0 else 0):.1f} 
   Gelen: %{(self.stats['bytes_from_device']/total_bytes*100 if total_bytes > 0 else 0):.1f}"""
            
            messagebox.showinfo("İstatistikler", stats_text)
        else:
            messagebox.showinfo("İstatistikler", "📊 Henüz veri işlenmedi!\nÖnce sniffing başlatın.")
    
    def show_port_scanner(self):
        """Port tarayıcı penceresini göster"""
        scanner_window = tk.Toplevel(self.root)
        scanner_window.title("🔍 Port Tarayıcısı")
        scanner_window.geometry("600x400")
        scanner_window.transient(self.root)
        scanner_window.grab_set()
        
        # Ana frame
        main_frame = ttk.Frame(scanner_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Üst panel
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(top_frame, text="🔄 Tarama", 
                  command=lambda: self.scan_ports(port_tree)).pack(side=tk.LEFT)
        ttk.Label(top_frame, text="Mevcut COM Portları:").pack(side=tk.LEFT, padx=(20, 0))
        
        # Port listesi
        port_tree = ttk.Treeview(main_frame, columns=("Port", "Açıklama", "Üretici", "VID", "PID"), show="headings")
        
        # Sütun başlıkları
        port_tree.heading("Port", text="Port")
        port_tree.heading("Açıklama", text="Açıklama")
        port_tree.heading("Üretici", text="Üretici")
        port_tree.heading("VID", text="VID")
        port_tree.heading("PID", text="PID")
        
        # Sütun genişlikleri
        port_tree.column("Port", width=80)
        port_tree.column("Açıklama", width=200)
        port_tree.column("Üretici", width=150)
        port_tree.column("VID", width=60)
        port_tree.column("PID", width=60)
        
        port_tree.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=port_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        port_tree.configure(yscrollcommand=scrollbar.set)
        
        # İlk taramayı yap
        self.scan_ports(port_tree)
    
    def scan_ports(self, tree_widget):
        """Portları tara ve listele"""
        # Mevcut öğeleri temizle
        for item in tree_widget.get_children():
            tree_widget.delete(item)
        
        try:
            ports = serial.tools.list_ports.comports()
            for port in ports:
                vid = f"0x{port.vid:04X}" if port.vid else "N/A"
                pid = f"0x{port.pid:04X}" if port.pid else "N/A"
                
                tree_widget.insert("", tk.END, values=(
                    port.device,
                    port.description or "N/A",
                    port.manufacturer or "N/A",
                    vid,
                    pid
                ))
        except Exception as e:
            messagebox.showerror("Hata", f"Port tarama hatası: {str(e)}")
    
    def show_about(self):
        """Hakkında penceresini göster"""
        about_text = """🔍 USB/Serial Sniffer v1.0

📋 Özellikler:
• İki serial port arasındaki veri akışını izleme
• Hex ve ASCII görüntüleme
• Ayrı ve birleşik veri görünümleri
• Detaylı istatistikler
• Log kaydetme
• Port tarayıcısı

👨‍💻 Geliştirici: Python ile geliştirilmiştir
📅 Tarih: 2025
🛠 Teknolojiler: Python, tkinter, pyserial

⚠ Uyarı: Bu araç eğitim ve test amaçlıdır.
Yasal sorumluluk kullanıcıya aittir."""

        messagebox.showinfo("Hakkında", about_text)
    
    def show_help(self):
        """Yardım penceresini göster"""
        help_window = tk.Toplevel(self.root)
        help_window.title("❓ Kullanım Kılavuzu")
        help_window.geometry("700x500")
        help_window.transient(self.root)
        help_window.grab_set()
        
        # ScrolledText widget
        help_text = scrolledtext.ScrolledText(help_window, font=("Segoe UI", 10), wrap=tk.WORD)
        help_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        help_content = """📖 USB/Serial Sniffer Kullanım Kılavuzu

🚀 BAŞLANGIÇ:
1. İki COM portu seçin:
   - Sanal Port: com0com veya benzer sanal port çifti
   - Fiziksel Port: Gerçek USB cihazınız
   
2. Doğru baud rate'i ayarlayın
3. "Başlat" butonuna tıklayın

🔧 KURULUM:
• com0com kurulumu gereklidir (sanal port çifti için)
• Uygulama → Sanal Port → Fiziksel Cihaz şeklinde bağlantı yapın

📊 GÖRÜNÜMLER:
• Ayrı Paneller: Giden ve gelen veriler ayrı panellerde
• Birleşik Görünüm: Tüm veri akışı zaman sıralı
• Raw Hex: Sadece hex değerler

⚙ ÖZELLİKLER:
• F5: Portları yenile
• Ctrl+L: Ekranı temizle  
• Ctrl+S: Dosya kaydet
• Renkli veri gösterimi (Kırmızı: Giden, Mavi: Gelen)

🔍 TARAMA:
• Araçlar → Port Tarayıcısı ile tüm portları inceleyin
• VID/PID bilgilerini görün

💾 KAYDETME:
• Tüm görünümler tek dosyada kaydedilir
• Otomatik zaman damgası eklenir

⚠ UYARI:
• Aynı portu hem sanal hem fiziksel olarak seçmeyin
• Port kullanımda ise başka uygulamaları kapatın
• Yüksek veri hızında performans düşebilir"""

        help_text.insert(tk.END, help_content)
        help_text.config(state=tk.DISABLED)
    
    def setup_timer(self):
        """GUI güncelleme zamanlayıcısını ayarla"""
        def timer_callback():
            self.process_gui_queue()
            self.update_stats()
            self.root.after(100, timer_callback)  # 100ms'de bir güncelle
        
        # İlk çağrı
        self.root.after(100, timer_callback)
    
    def run(self):
        """Uygulamayı çalıştır"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Temizlik işlemleri"""
        if hasattr(self, 'worker') and self.worker:
            self.worker.stop_monitoring()

# Ana çalıştırma bloğu
if __name__ == "__main__":
    try:
        app = SerialSnifferGUI()
        app.run()
    except Exception as e:
        print(f"Uygulama hatası: {e}")
        import traceback
        traceback.print_exc()