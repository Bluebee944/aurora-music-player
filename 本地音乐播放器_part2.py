        header.pack(fill="x", padx=26, pady=(22, 6))
        title_col = tk.Frame(header, bg=self.MAIN_BG)
        title_col.pack(side="left")
        tk.Label(title_col, text="本地音乐", bg=self.MAIN_BG, fg="#F2F2F5",
                 font=("Microsoft YaHei UI", 24, "bold")).pack(anchor="w")
        self.count_label = tk.Label(title_col, text="共 0 首歌曲 · 总时长 0 分钟",
                                    bg=self.MAIN_BG, fg=TEXT_DIM,
                                    font=("Microsoft YaHei UI", 10))
        self.count_label.pack(anchor="w", pady=(4, 0))
        btns = tk.Frame(header, bg=self.MAIN_BG)
        btns.pack(side="right")
        self._action_btn(btns, "随机播放", self._shuffle_all).pack(side="left", padx=(0, 10))
        self._action_btn(btns, "播放全部", self._play_all, primary=True).pack(side="left")

        self.status_label = tk.Label(self.list_view, text="", bg=self.MAIN_BG, fg=TEXT_DIM,
                                     font=("Microsoft YaHei UI", 9))
        self.status_label.pack(anchor="w", padx=26, pady=(0, 4))

        # 歌曲列表（Treeview，Aurora 样式，行 = playlist 索引 iid）
        list_body = tk.Frame(self.list_view, bg=self.MAIN_BG)
        list_body.pack(fill="both", expand=True, padx=12, pady=(0, 16))
        self.side_list = ttk.Treeview(
            list_body, columns=("idx", "title", "artist", "album", "dur"),
            show="headings", style="Aurora.Treeview", selectmode="browse")
        self.side_list.heading("idx", text="#")
        self.side_list.heading("title", text="标题")
        self.side_list.heading("artist", text="歌手")
        self.side_list.heading("album", text="专辑")
        self.side_list.heading("dur", text="时长")
        self.side_list.column("idx", width=48, minwidth=40, stretch=False, anchor="center")
        self.side_list.column("title", width=320, minwidth=160, stretch=True, anchor="w")
        self.side_list.column("artist", width=150, minwidth=100, stretch=False, anchor="w")
        self.side_list.column("album", width=170, minwidth=100, stretch=False, anchor="w")
        self.side_list.column("dur", width=66, minwidth=50, stretch=False, anchor="e")
        side_vsb = SlimScrollbar(list_body, command=self.side_list.yview)
        self.side_list.configure(yscrollcommand=side_vsb.set)
        self.side_list.pack(side="left", fill="both", expand=True, padx=(14, 0))
        self.side_list.bind("<Double-1>", self._on_side_double)
        self.side_list.bind("<ButtonPress-1>", self._drag_start)
        self.side_list.bind("<B1-Motion>", self._drag_motion)
        self.side_list.bind("<ButtonRelease-1>", self._drag_end)
        self.side_list.bind("<Button-3>", self._on_row_menu)
        # 隐藏式滚动条：平时不可见，滚动时才显示，停留片刻后自动隐藏
        self.side_vsb = side_vsb
        self._sb_hide_after = None

        def _sb_show():
            side_vsb.place(relx=1.0, rely=0.0, anchor="ne", relheight=1.0)

        def _sb_hide():
            side_vsb.place_forget()

        def _sb_schedule_hide(ms=700):
            if self._sb_hide_after is not None:
                self.root.after_cancel(self._sb_hide_after)
            self._sb_hide_after = self.root.after(ms, _sb_hide)

        def _sb_on_scroll(event):
            tree = self.side_list
            step = -int(event.delta / 120) * 3
            tree.yview_scroll(step, "units")
            if tree.yview() == (0.0, 1.0):
                return "break"
            _sb_show()
            _sb_schedule_hide()
            return "break"

        self.side_list.bind("<MouseWheel>", _sb_on_scroll)
        self.side_list.bind("<Leave>", lambda _e: _sb_schedule_hide(300))
        side_vsb.bind("<ButtonPress-1>", lambda _e: _sb_schedule_hide(60000))
        side_vsb.bind("<ButtonRelease-1>", lambda _e: _sb_schedule_hide(700))

        # 歌曲右键菜单
        self.song_menu = tk.Menu(self.root, tearoff=0)
        self.song_menu.add_command(label="播放", command=self._menu_play)
        self.song_menu.add_command(label="下一首播放", command=self._menu_play_next)
        self.song_menu.add_separator()
        self.song_menu.add_command(label="收藏", command=self._menu_toggle_fav)
        self.song_menu.add_command(label="封面来源：内嵌/联网", command=self._toggle_cover_source)
        self.song_menu.add_separator()
        self.song_menu.add_command(label="从播放列表移除", command=self._menu_remove)
        self.song_menu.add_command(label="清空播放列表", command=self._menu_clear)

        # ---- 歌词视图 ----
        self.lyric_view = tk.Frame(content, bg=self.MAIN_BG)
        top = tk.Frame(self.lyric_view, bg=self.MAIN_BG)
        top.pack(fill="x", padx=30, pady=(26, 6))
        cover_box = tk.Frame(top, bg=COVER_PLACEHOLDER, width=168, height=168)
        cover_box.pack(side="left")
        cover_box.pack_propagate(False)
        self.now_cover_label = tk.Label(cover_box, text="♪", bg=COVER_PLACEHOLDER,
                                        fg="white", font=("Microsoft YaHei UI", 42, "bold"))
        self.now_cover_label.pack(fill="both", expand=True)
        info = tk.Frame(top, bg=self.MAIN_BG)
        info.pack(side="left", fill="both", expand=True, padx=(22, 0), pady=(30, 0))
        self.now_title_label = tk.Label(info, text="未播放", bg=self.MAIN_BG, fg="#F2F2F5",
                                        font=("Microsoft YaHei UI", 20, "bold"), anchor="w")
        self.now_title_label.pack(fill="x")
        self.now_artist_label = tk.Label(info, text="选择歌曲开始播放", bg=self.MAIN_BG,
                                         fg=TEXT_GRAY,
                                         font=("Microsoft YaHei UI", 11), anchor="w")
        self.now_artist_label.pack(fill="x", pady=(6, 0))

        lyric_body = tk.Frame(self.lyric_view, bg=self.MAIN_BG)
        lyric_body.pack(fill="both", expand=True, padx=30, pady=(8, 24))
        self.lyric_text = tk.Text(lyric_body, wrap="word", font=("Microsoft YaHei UI", 12),
                                  bg=self.MAIN_BG, fg=TEXT_GRAY, relief="flat",
                                  padx=10, pady=10, spacing1=6, spacing3=6,
                                  selectbackground=CARD)
        self.lyric_text.pack(side="left", fill="both", expand=True)
        self.lyric_sb = SlimScrollbar(lyric_body, command=self.lyric_text.yview)
        self.lyric_text.configure(yscrollcommand=self.lyric_sb.set)
        self.lyric_sb.pack(side="right", fill="y", pady=8)
        self.lyric_text.tag_configure("center", justify="center")
        self.lyric_text.tag_configure("cur", foreground=ACCENT,
                                      font=("Microsoft YaHei UI", 14, "bold"))
        self.lyric_text.tag_configure("normal", foreground=TEXT_GRAY)
        self.lyric_text.tag_configure("meta", foreground=TEXT_DIM)
        self.lyric_text.config(state="disabled")
        self._set_lyric_text("选择左侧歌曲开始播放\n歌词将在这里同步显示")

        # 默认显示列表视图
        self.list_view.pack(fill="both", expand=True)

    def _switch_view(self, view):
        if view == self._view:
            return
        self._view = view
        if view == "queue":
            self._show_queue_panel()
            return
        if view == "lyric":
            self.list_view.pack_forget()
            self.lyric_view.pack(fill="both", expand=True)
        else:
            self.lyric_view.pack_forget()
            self.list_view.pack(fill="both", expand=True)
        for v, item in getattr(self, "_nav_btns", {}).items():
            active = (v == view)
            item.configure(bg=self.SIDEBAR_ACTIVE_BG if active else self.SIDEBAR_BG)
            for child in item.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(fg=ACCENT if active else "#C9CBD2")
                else:
                    child.configure(bg=ACCENT if active else self.SIDEBAR_BG)

    def _show_queue_panel(self):
        top = tk.Toplevel(self.root)
        top.title("播放队列")
        top.configure(bg=CARD)
        top.resizable(False, False)
        tk.Label(top, text="下一首播放", bg=CARD, fg="#EDEDF0",
                 font=("Microsoft YaHei UI", 12, "bold")).pack(anchor="w", padx=16, pady=(12, 6))
        box = tk.Frame(top, bg=CARD)
        box.pack(fill="both", expand=True, padx=16)
        if self.up_next:
            for i in self.up_next[:20]:
                if 0 <= i < len(self.playlist):
                    _p, t, a, _d = self.playlist[i]
                    tk.Label(box, text="%s - %s" % (a, t), bg=CARD, fg="#C4C4D0",
                             font=("Microsoft YaHei UI", 10), anchor="w").pack(fill="x", pady=2)
        else:
            tk.Label(box, text="队列为空", bg=CARD, fg=TEXT_DIM,
                     font=("Microsoft YaHei UI", 10)).pack(anchor="w", pady=6)
        def _clear():
            self.up_next = []
            top.destroy()
        btns = tk.Frame(top, bg=CARD)
        btns.pack(pady=(6, 14))
        tk.Button(btns, text="清空队列", command=_clear, relief="flat", bd=0,
                  bg="#23232B", fg="#C4C4D0", activebackground="#2A2A33",
                  activeforeground="#EDEDF0", padx=14, pady=6,
                  font=("Microsoft YaHei UI", 10), cursor="hand2"
                  ).pack(side="left", padx=(0, 8))
        tk.Button(btns, text="关闭", command=top.destroy, relief="flat", bd=0,
                  bg=ACCENT, fg="#0B1A12", activebackground="#35E88C",
                  activeforeground="#0B1A12", padx=18, pady=6,
                  font=("Microsoft YaHei UI", 10, "bold"), cursor="hand2"
                  ).pack(side="left")
        top.geometry("+%d+%d" % (self.root.winfo_x() + 120,
                                 self.root.winfo_y() + 100))
        top.transient(self.root)
        top.grab_set()

    def _action_btn(self, parent, text, command, primary=False):
        return tk.Button(parent, text=text, command=command, relief="flat", bd=0,
                         bg=ACCENT if primary else "#1E1E26",
                         fg="#0B1A12" if primary else "#C4C4D0",
                         activebackground="#35E88C" if primary else "#272730",
                         activeforeground="#0B1A12" if primary else "#EDEDF0",
                         padx=18, pady=8,
                         font=("Microsoft YaHei UI", 10,
                               "bold" if primary else "normal"),
                         cursor="hand2")

    def _shuffle_all(self):
        """随机播放：切到随机模式并随机播放一首。"""
        if not self.playlist:
            return
        self.mode = "shuffle"
        self.mode_btn.set_mode("shuffle")
        self._play_index(random.randrange(len(self.playlist)))

    def _bar_btn(self, parent, text, command, accent=False, font_size=None):
        """底部条文字按钮：深色底灰字（Aurora ghost 样式）。"""
        return tk.Button(parent, text=text, command=command, relief="flat", bd=0,
                         bg="#23232B", fg="#C4C4D0",
                         activebackground="#2A2A33", activeforeground="#EDEDF0",
                         padx=14 if accent else 10, pady=6,
                         font=("Microsoft YaHei UI", font_size or 10,
                               "bold" if accent else "normal"),
                         cursor="hand2")

    def _build_bottom_bar(self, root):
        bar = tk.Frame(root, bg=self.BAR_BG, height=92)
        bar.pack(side="bottom", fill="x")
        bar.pack_propagate(False)
        tk.Frame(bar, bg=BORDER, height=1).pack(side="top", fill="x")

        # 左：封面缩略图 + 歌名/歌手
        left = tk.Frame(bar, bg=self.BAR_BG)
        left.pack(side="left", fill="y", padx=(22, 0))
        left.pack_propagate(False)
        left.config(width=250)
        cover_box = tk.Frame(left, bg=COVER_PLACEHOLDER, width=56, height=56)
        cover_box.pack(side="left", pady=18)
        cover_box.pack_propagate(False)
        self.cover_label = tk.Label(cover_box, text="♪", bg=COVER_PLACEHOLDER, fg="white",
                                    font=("Microsoft YaHei UI", 18, "bold"))
        self.cover_label.pack(fill="both", expand=True)
        info = tk.Frame(left, bg=self.BAR_BG)
        info.pack(side="left", padx=(12, 0))
        info.pack_propagate(False)
        info.config(width=170, height=48)
        self.playing_title = MarqueeLabel(info, bg=self.BAR_BG, fg="#EDEDF0",
                                          root=self.root,
                                          font=("Microsoft YaHei UI", 11, "bold"))
        self.playing_title.pack(anchor="w")
        self.playing_artist = tk.Label(info, text="选择一首歌开始", bg=self.BAR_BG,
                                       fg="#7A7A86", font=("Microsoft YaHei UI", 10))
        self.playing_artist.pack(anchor="w", pady=(4, 0))

        # 中：控制按钮行（进度条上方，居中） + 进度条行（下移）
        center = tk.Frame(bar, bg=self.BAR_BG)
        controls_row = tk.Frame(center, bg=self.BAR_BG)
        controls_row.pack(fill="x", padx=18, pady=(10, 2))
        controls_row.grid_columnconfigure(0, weight=1)
        controls_row.grid_columnconfigure(4, weight=1)
        self.prev_btn = RoundIconButton(controls_row, "prev", command=self._prev,
                                        width=30, height=30)
        self.prev_btn.grid(row=0, column=1, padx=7)
        self.play_btn = PlayButton(controls_row, command=self._toggle_play,
                                   color=self.ACCENT, size=32)
        self.play_btn.grid(row=0, column=2, padx=7)
        self.next_btn = RoundIconButton(controls_row, "next", command=self._next,
                                        width=30, height=30)
        self.next_btn.grid(row=0, column=3, padx=7)

        prog = tk.Frame(center, bg=self.BAR_BG)
        prog.pack(fill="x", padx=18, pady=(2, 10))
        self.time_label = tk.Label(prog, text="00:00", bg=self.BAR_BG, fg="#6E6E7A",
                                   font=("Consolas", 9))
        self.time_label.pack(side="left")
        self.progress = WebProgressBar(prog, command=self._on_web_seek)
        self.progress.pack(side="left", fill="x", expand=True, padx=10, pady=4)
        self.dur_label = tk.Label(prog, text="00:00", bg=self.BAR_BG, fg="#6E6E7A",
                                  font=("Consolas", 9))
        self.dur_label.pack(side="left")

        # 右：循环 -> 播放列表 -> 音量（播放/上一曲/下一曲已移至中间控制行）
        right = tk.Frame(bar, bg=self.BAR_BG)
        right.pack(side="right", fill="y", padx=(0, 20))
        self.mode_btn = ModeIconButton(right, mode=self.mode,
                                       command=self._toggle_mode, size=40)
        self.mode_btn.pack(side="left", padx=(0, 10))

        # 播放列表（打开队列面板）
        self._list_img = ImageTk.PhotoImage(_pil_icon(34, _draw_icon_list))
        self.list_btn = tk.Label(right, image=self._list_img, bg=self.BAR_BG, cursor="hand2")
        self.list_btn.pack(side="left", padx=(0, 12))
        self.list_btn.bind("<Button-1>", lambda _e: self._show_queue_panel())

        # 音量
        self.vol_btn = ImageIconButton(right, _draw_icon_speaker,
                                       command=self._toggle_volume_panel, size=38)
        self.vol_btn.pack(side="left", padx=(0, 10))

        center.pack(side="left", fill="both", expand=True, padx=(8, 6))

    # ---------- 歌单扫描 ----------

    @staticmethod
    def _parse_filename(path):
        """从文件名解析 (歌名, 歌手)：支持「歌手 - 歌名.ext」格式。"""
        name = os.path.splitext(os.path.basename(path))[0]
        if " - " in name:
            parts = name.rsplit(" - ", 1)
            return parts[1].strip(), parts[0].strip()
        return name.strip(), "未知歌手"

    def _scan(self, folder):
        folder = folder or DEFAULT_MUSIC_DIR
        self.dir_var.set(folder)
        files = []
        if os.path.isdir(folder):
            for dirpath, _dirs, filenames in os.walk(folder):
                for fn in filenames:
                    if fn.lower().endswith(MUSIC_EXTS):
                        files.append(os.path.join(dirpath, fn))
        files.sort(key=lambda p: os.path.basename(p).lower())

        self.playlist = []
        for p in files:
            title, artist = self._parse_filename(p)
            self.playlist.append((p, title, artist, get_duration_seconds(p)))

        self._update_count()
        self.up_next = []
        self.play_history = []
        if self.current_path is not None:
            pos = next((i for i, e in enumerate(self.playlist) if e[0] == self.current_path), -1)
            if pos >= 0:
                self.current_index = pos
            else:
                self._stop_playback()
                self.current_index = -1
                self.current_path = None
        else:
            self.current_index = -1
        if not files:
            self.status_label.config(
                text="该文件夹中没有找到音乐文件（支持 mp3 / flac / wav / ogg）")
            if not self.playing:
                self.playing_title.set_text("未在播放")
                self.playing_artist.config(text="选择一首歌开始")
        else:
            self.status_label.config(text="双击播放 · 右键更多操作 · 按住行拖动排序")
        self._refresh_side_list()

    def _update_count(self):
        """更新头部计数：共 N 首歌曲 · 总时长。"""
        n = len(self.playlist)
        total = sum(t[3] for t in self.playlist)
        h = total // 3600
        m = (total % 3600) // 60
        if h:
            text = "共 %d 首歌曲 · 总时长 %d 小时 %d 分钟" % (n, h, m)
        else:
            text = "共 %d 首歌曲 · 总时长 %d 分钟" % (n, m)
        try:
            self.count_label.config(text=text)
        except Exception:
            pass

    def _refresh_side_list(self):
        """重建歌曲列表（Treeview，当前播放行高亮；支持搜索过滤）。"""
        if not hasattr(self, "side_list"):
            return
        tree = self.side_list
        try:
            tree.delete(*tree.get_children())
        except Exception:
            return
        kw = getattr(self, "search_kw", "").strip().lower()
        for pos, (_p, title, artist, dur) in enumerate(self.playlist):
            if kw and kw not in ("%s%s" % (title, artist)).lower():
                continue
            label = title if not artist or artist == "未知歌手" else "%s - %s" % (artist, title)
            tree.insert("", "end", iid=str(pos),
                        values=(pos + 1, label, artist, "未知专辑", fmt_time(dur)))
        if 0 <= self.current_index < len(self.playlist):
            try:
                tree.selection_set(str(self.current_index))
                tree.see(str(self.current_index))
            except Exception:
                pass

    def _on_side_double(self, event):
        """双击歌曲行播放。"""
        iid = self.side_list.identify_row(event.y)
        if iid:
            self._play_index(int(iid))

    # ---------- 拖拽排序 ----------

    def _drag_start(self, event):
        iid = self.side_list.identify_row(event.y)
        self._drag_idx = int(iid) if iid else -1
        self._drag_ok = self._drag_idx >= 0

    def _drag_motion(self, event):
        if not getattr(self, "_drag_ok", False):
            return
        iid = self.side_list.identify_row(event.y)
        if iid and int(iid) != self._drag_idx:
            self._move_row(self._drag_idx, int(iid))
            self._drag_idx = int(iid)

    def _drag_end(self, _event):
        self._drag_ok = False

    def _move_row(self, src, dst):
        """把 src 行移动到 dst 行位置（同步播放列表与当前播放）。"""
        if src == dst:
            return
        entry = self.playlist.pop(src)
        self.playlist.insert(dst, entry)
        if src < dst:
            self.up_next = [dst if i == src else (i - 1 if src < i <= dst else i)
                            for i in self.up_next]
        else:
            self.up_next = [dst if i == src else (i + 1 if dst <= i < src else i)
                            for i in self.up_next]
        if self.current_path is not None:
            for pos, (p, _t, _a, _d) in enumerate(self.playlist):
                if p == self.current_path:
                    self.current_index = pos
                    break
        self._refresh_side_list()

    def _choose_dir(self):
        folder = filedialog.askdirectory(initialdir=self.dir_var.get(),
                                         title="选择音乐文件夹")
        if folder:
            self._scan(folder)

    def _refresh_dir(self):
        self._scan(self.dir_var.get().strip())

    # ---------- 播放控制 ----------

    def _play_index(self, idx):
        if not self.playlist or not (0 <= idx < len(self.playlist)):
            return
        if not self._audio_ok:
            messagebox.showwarning("无法播放", "音频设备不可用，请检查 pygame 安装与系统音频。")
            return
        path, title, artist, dur = self.playlist[idx]
        self._decode_token += 1
        token = self._decode_token
        try:
            pygame.mixer.music.load(path)
        except Exception:
            self._start_decode_play(idx, token)
            return
        self._start_playback(path, title, artist, dur, idx, token)

    def _start_decode_play(self, idx, token):
        """后台解码：状态栏提示，完成后回到主线程继续播放。"""
        path, title, artist, dur = self.playlist[idx]
        try:
            self.status_label.config(text="正在解码 %s …" % title)
        except Exception:
            pass

        def worker():
            play_path = self._ensure_wav(path)
            self.root.after(0, lambda: self._on_decode_done(idx, token, play_path))

        threading.Thread(target=worker, daemon=True).start()

    def _on_decode_done(self, idx, token, play_path):
        """解码完成回调（主线程）。"""
        if token != self._decode_token:
            return
        if not play_path:
            try:
                messagebox.showerror(
                    "无法加载",
                    "无法加载该音频文件（已尝试内置解码器）：\n%s" % self.playlist[idx][1])
            except Exception:
                pass
            try:
                self.status_label.config(text="无法加载该音频文件")
            except Exception:
                pass
            return
        try:
            pygame.mixer.music.load(play_path)
        except Exception as exc:
            messagebox.showerror("无法加载", "无法加载该音频文件：\n%s\n%s" % (self.playlist[idx][1], exc))
            return
        path, title, artist, dur = self.playlist[idx]
        self._start_playback(path, title, artist, dur, idx, token)

    def _start_playback(self, path, title, artist, dur, idx, token):
        """真正开始播放（主线程）。"""
        if token != self._decode_token:
            return
        self.current_index = idx
        self.current_path = path
        self.play_history.append(idx)
        if len(self.play_history) > 200:
            self.play_history.pop(0)
        self.pos = 0.0
        self._play_base = 0.0
        self.play_started_at = time.time()
        self.paused = False
        self.playing = True
        pygame.mixer.music.set_volume(self.volume)
        pygame.mixer.music.play()
        self.duration = dur
        self._set_play_text("暂停")
        self.playing_title.set_text(title)
        self.playing_artist.config(text=artist)
        self._set_song_info(title, artist, dur)
        if hasattr(self, "side_list"):
            try:
                self.side_list.selection_set(str(idx))
                self.side_list.see(str(idx))
            except Exception:
                pass
        self._update_covers(path)
        self._load_lyrics_async(path)
        self._update_fav_icon()
        try:
            self.root.lift()
        except Exception:
            pass

    def _toggle_mode(self):
        """循环切换播放模式：列表循环 -> 单曲循环 -> 随机播放。"""
        self.mode = {"list": "single", "single": "shuffle", "shuffle": "list"}[self.mode]
        self.mode_btn.set_mode(self.mode)

    def _play_all(self):
        """播放全部：从列表第一首开始。"""
        if self.playlist:
            self._play_index(0)

    def _set_play_text(self, text):
        """更新圆形播放按钮：暂停显示 ❚❚，其余显示 ▶。"""
        self.play_btn.set_playing(text == "暂停")

    def _fav_base_dir(self):
        """收藏持久化目录：exe/脚本所在目录。"""
        try:
            if getattr(sys, "frozen", False):
                return os.path.dirname(sys.executable)
        except Exception:
            pass
        return os.path.dirname(os.path.abspath(__file__))

    def _fav_file(self):
        return os.path.join(self._fav_base_dir(), "favorites.json")

    def _load_favs(self):
        try:
            p = self._fav_file()
            if os.path.exists(p):
                with io.open(p, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self.favorites = set(str(x) for x in data)
        except Exception:
            pass

    def _save_favs(self):
        try:
            with io.open(self._fav_file(), "w", encoding="utf-8") as f:
                json.dump(sorted(self.favorites), f, ensure_ascii=False, indent=1)
        except Exception:
            pass

    def _is_fav(self, path=None):
        p = path if path is not None else self.current_path
        return bool(p and p in self.favorites)

    def _toggle_fav(self):
        """收藏/取消收藏当前歌曲。"""
        p = self.current_path
        if not p:
            return
        if p in self.favorites:
            self.favorites.discard(p)
        else:
            self.favorites.add(p)
        self._save_favs()
        self._update_fav_icon()
        try:
            self.status_label.config(
                text="已收藏：%s" % self.playing_title.cget("text") if p in self.favorites
                else "已取消收藏")
        except Exception:
            pass

    def _update_fav_icon(self):
        if not hasattr(self, "fav_btn"):
            return
        try:
            self.fav_btn.config(image=self._fav_imgs[self._is_fav()])
        except Exception:
            pass

    def _menu_toggle_fav(self):
        """右键菜单：收藏/取消收藏目标行歌曲。"""
        if 0 <= self._menu_pos < len(self.playlist):
            p = self.playlist[self._menu_pos][0]
            if p in self.favorites:
                self.favorites.discard(p)
            else:
                self.favorites.add(p)
            self._save_favs()
            self._update_fav_icon()
            try:
                self.status_label.config(
                    text="已收藏" if p in self.favorites else "已取消收藏")
            except Exception:
                pass

    def _on_cover_btn_hover(self, on):
        self._cover_btn_hovering = on
        try:
            if on:
                src = "联网抓取（按歌手-歌名）" if self.cover_source == "online" else "内嵌封面"
                self.status_label.config(text="封面来源：%s（点击切换）" % src)
        except Exception:
            pass

    def _toggle_cover_source(self):
        """切换封面来源：内嵌封面 / 联网抓取（按歌手-歌名）。"""
        self.cover_source = "online" if self.cover_source == "embedded" else "embedded"
        try:
            src = "联网抓取（按歌手-歌名）" if self.cover_source == "online" else "内嵌封面"
            self.status_label.config(text="封面来源：%s" % src)
        except Exception:
            pass
        if self.current_path is not None:
            self._update_covers(self.current_path)

    def _toggle_play(self):
        if self.current_index < 0:
            if self.playlist:
                self._play_index(0)
            return
        if not self.playing:
            if self.paused:
                self._resume()
            else:
                self._play_index(self.current_index)
        else:
            self._pause()

    def _pause(self):
        if not self.playing or self.paused:
            return
        try:
            gp = pygame.mixer.music.get_pos()
            if gp is not None and gp >= 0:
                self.pos = self._play_base + gp / 1000.0
            elif self.play_started_at is not None:
                self.pos += time.time() - self.play_started_at
        except Exception:
            if self.play_started_at is not None:
                self.pos += time.time() - self.play_started_at
        pygame.mixer.music.pause()
        self.play_started_at = None
        self.paused = True
        self._set_play_text("继续")

    def _resume(self):
        if not self.paused:
            return
        pygame.mixer.music.unpause()
        self.play_started_at = time.time()
        self.paused = False
        self._set_play_text("暂停")

    def _next_index_core(self):
        """计算下一首索引：优先消费“下一首播放”队列。"""
        if self.up_next:
            return self.up_next.pop(0)
        n = len(self.playlist)
        if self.mode == "shuffle":
            if n <= 1:
                return self.current_index if self.current_index >= 0 else 0
            others = [i for i in range(n) if i != self.current_index]
            return random.choice(others)
        if self.current_index < 0:
            return 0
        return (self.current_index + 1) % n

    def _next(self):
        """手动下一首。"""
        if not self.playlist:
            return
        idx = self._next_index_core()
        if 0 <= idx < len(self.playlist):
            self._play_index(idx)

    def _prev(self):
        """手动上一首。"""
        if not self.playlist:
            return
        if self.current_index < 0:
            self._play_index(0)
            return
        if self._current_sec() > 3:
            self._seek(0.0)
            return
        if self.mode == "shuffle" and len(self.play_history) >= 2:
            self.play_history.pop()
            self._play_index(self.play_history.pop())
            return
        self._play_index((self.current_index - 1) % len(self.playlist))

    def _current_sec(self):
        """权威时间源：播放中优先用 pygame 实际输出位置（与听到的声音同步）。"""
        if self.playing and not self.paused and self._audio_ok:
            try:
                gp = pygame.mixer.music.get_pos()
                if gp is not None and gp >= 0:
                    return self._play_base + gp / 1000.0
            except Exception:
                pass
        if self.play_started_at is not None:
            return self.pos + (time.time() - self.play_started_at)
        return self.pos

    def _seek(self, sec):
        sec = max(0.0, sec)
        if self.playing and self._audio_ok:
            try:
                pygame.mixer.music.play(start=sec)
            except Exception:
                return
        self._play_base = sec
        self.pos = sec
        if self.paused:
            if self._audio_ok:
                pygame.mixer.music.pause()
            self.play_started_at = None
        else:
            self.play_started_at = time.time()

    def _on_web_seek(self, ratio, final):
        """进度条回调：ratio 0..1，final=True 时真正跳转。"""
        sec = ratio * (self.duration if self.duration > 0 else 0)
        self._drag_target = sec
        if not final:
            self._seeking = True
            self.time_label.config(text=fmt_time(sec))
        else:
            self._seeking = False
            self._seek(sec)

    def _apply_vol(self, value):
        """应用音量（0..100）。"""
        self.volume = max(0.0, min(1.0, float(value) / 100.0))
        if self._audio_ok:
            try:
                pygame.mixer.music.set_volume(self.volume)
            except Exception:
                pass
        if self._vol_slider is not None:
            try:
                self._vol_slider.set_value(int(round(self.volume * 100)))
            except Exception:
                pass

    def _toggle_volume_panel(self):
        """音量按钮：弹出/收起竖向音量滑杆面板。"""
        if self._vol_panel is not None and self._vol_panel.winfo_exists():
            self._hide_volume_panel()
            return
        panel = tk.Toplevel(self.root)
        panel.overrideredirect(True)
        panel.configure(bg="#FFFFFF")
        box = tk.Frame(panel, bg="#FFFFFF")
        box.pack(padx=10, pady=10)
        slider = VolumeSlider(box, value=int(round(self.volume * 100)),
                              command=self._apply_vol, height=168, width=22)
        slider.pack()
        spk_img = ImageTk.PhotoImage(_pil_icon(22, lambda d, S: _draw_icon_speaker(d, S, "#666666")))
        spk = tk.Label(box, image=spk_img, bg="#FFFFFF")
        spk.pack(pady=(8, 0))
        box._spk_img = spk_img
        panel.update_idletasks()
        bw, bh = panel.winfo_reqwidth(), panel.winfo_reqheight()
        x = self.vol_btn.winfo_rootx() + self.vol_btn.winfo_width() // 2 - bw // 2
        y = self.vol_btn.winfo_rooty() - bh - 10
        if y < 0:
            y = 0
        panel.geometry("+%d+%d" % (x, y))
        panel.bind("<Button-1>", self._on_panel_click)
        panel.bind("<Escape>", lambda _e: self._hide_volume_panel())
        panel.lift()
        panel.focus_force()
        self._vol_panel = panel
        self._vol_slider = slider

    def _on_panel_click(self, event):
        if not isinstance(event.widget, VolumeSlider):
            self._hide_volume_panel()

    def _hide_volume_panel(self):
        if self._vol_panel is not None:
            try:
                self._vol_panel.destroy()
            except Exception:
                pass
        self._vol_panel = None
        self._vol_slider = None

    def _on_root_click(self, event):
        """点击主窗口非音量按钮区域时收起音量面板/桌面歌词面板。"""
        if event.widget is self.vol_btn:
            return
        self._hide_volume_panel()
        if self.desktop_lyrics is not None:
            self.desktop_lyrics._close_panel()

    # ---------- 播放列表操作 ----------

    def _ensure_wav(self, path):
        """pygame 无法直接解码时，用 PyAV 转临时 WAV 并返回路径；失败返回 None。"""
        try:
            h = hashlib.md5(path.encode("utf-8", errors="ignore")).hexdigest()[:10]
            tmp = os.path.join(tempfile.gettempdir(), "mmplayer_%s.wav" % h)
            if os.path.exists(tmp) and os.path.getsize(tmp) > 1024:
                return tmp
            if decode_to_wav(path, tmp):
                self._clean_wav_cache()
                return tmp
        except Exception:
            pass
        return None

    def _clean_wav_cache(self):
        """临时 WAV 缓存限容：最多保留 50 个或 800MB，超出删最旧的。"""
        try:
            entries = []
            for fn in os.listdir(tempfile.gettempdir()):
                if fn.startswith("mmplayer_") and fn.endswith(".wav"):
                    p = os.path.join(tempfile.gettempdir(), fn)
                    try:
                        entries.append((os.path.getmtime(p), os.path.getsize(p), p))
                    except OSError:
                        pass
            entries.sort()
            total = sum(sz for _, sz, _ in entries)
            while len(entries) > 50 or total > 800 * 1024 * 1024:
                _, sz, old = entries.pop(0)
                try:
                    os.remove(old)
                except OSError:
                    pass
                total -= sz
        except Exception:
            pass

    def _stop_playback(self):
        """停止当前播放并复位播放区状态。"""
        try:
            if self._audio_ok:
                pygame.mixer.music.stop()
        except Exception:
            pass
        self.playing = False
        self.paused = False
        self.play_started_at = None
        self.pos = 0.0
        self._play_base = 0.0
        self.duration = 0.0
        self._set_play_text("播放")
        self.playing_title.set_text("未在播放")
        self.playing_artist.config(text="选择一首歌开始")
        self._set_song_info("", "")
        self._set_cover_placeholder()
        self._update_fav_icon()

    def _remove_row(self, pos):
        """从播放列表移除指定行。"""
        if not (0 <= pos < len(self.playlist)):
            return
        removed = self.playlist.pop(pos)
        if self.current_path == removed[0]:
            self._stop_playback()
            self.current_index = -1
            self.current_path = None
        elif self.current_index > pos:
            self.current_index -= 1
        self.up_next = [i - 1 if i > pos else i for i in self.up_next if i != pos]
        self._update_count()
        if not self.playlist:
            self.status_label.config(text="播放列表为空")
        self._refresh_side_list()

    def _on_row_menu(self, event):
        iid = self.side_list.identify_row(event.y)
        if not iid:
            return
        idx = int(iid)
        if not (0 <= idx < len(self.playlist)):
            return
        self._menu_pos = idx
        try:
            if 0 <= idx < len(self.playlist):
                self.song_menu.entryconfig(
                    3, label="取消收藏" if self.playlist[idx][0] in self.favorites else "收藏")
        except Exception:
            pass
        try:
            self.side_list.selection_set(str(idx))
            self.side_list.see(str(idx))
        except Exception:
            pass
        try:
            self.song_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.song_menu.grab_release()

    def _menu_play(self):
        if 0 <= self._menu_pos < len(self.playlist):
            self._play_index(self._menu_pos)

    def _menu_play_next(self):
        if 0 <= self._menu_pos < len(self.playlist) and self._menu_pos != self.current_index:
            self.up_next.insert(0, self._menu_pos)
            self.status_label.config(
                text="已加入下一首播放：%s" % self.playlist[self._menu_pos][1])

    def _menu_remove(self):
        self._remove_row(self._menu_pos)

    def _menu_clear(self):
        while self.playlist:
            self._remove_row(0)
        self.status_label.config(text="播放列表已清空")

    # ---------- 定时刷新 ----------

    def _tick(self):
        try:
            self._refresh_progress()
            self._check_song_end()
            self._refresh_lyric()
        except Exception:
            pass
        self.root.after(200, self._tick)

    def _refresh_progress(self):
        if self._seeking:
            return
        sec = self._current_sec()
        if self.duration > 0:
            self.progress.set_ratio(min(sec, self.duration) / self.duration)
        else:
            self.progress.set_ratio(0)
        self.time_label.config(text=fmt_time(sec))
        self.dur_label.config(text=fmt_time(self.duration) if self.duration > 0 else "00:00")

    def _check_song_end(self):
        if (self.playing and not self.paused and self._audio_ok
                and self.play_started_at is not None
                and not pygame.mixer.music.get_busy()):
            if self.mode == "single":
                self._play_index(self.current_index)
            else:
                self._next()

    # ---------- 歌词 ----------

    def _load_lyrics_async(self, path):
        title, artist = self._parse_filename(path)
        self.lyrics = []
        self.lyric_idx = -1
        self.lyric_offset_ms = 0
        self._set_lyric_text("正在联网获取歌词：《%s》…" % title)
        seq = getattr(self, "_lyric_seq", 0) + 1
        self._lyric_seq = seq

        def worker():
            try:
                lrc, src = fetch_lyrics(title, artist)
            except Exception:
                lrc, src = "", ""
            if getattr(self, "_lyric_seq", 0) == seq:
                self.root.after(0, lambda: self._apply_lyrics(lrc, src, title))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_lyrics(self, lrc, src, title):
        if not lrc or not lrc.strip():
            self._set_lyric_text(
                "未找到《%s》的歌词\n\n可尝试：\n"
                "1. 把文件名改成「歌手 - 歌名.mp3」格式后点「刷新」再播一次；\n"
                "2. 稍后重试，歌词接口偶尔会限流。" % title)
            return
        self.lyrics = parse_lrc(lrc)
        if not self.lyrics:
            self._set_lyric_text("已获取《%s》的歌词，但没有可同步的时间轴。\n\n来源：%s" % (title, src))
            return
        self.lyric_text.config(state="normal")
        self.lyric_text.delete("1.0", "end")
        for line in self.lyrics:
            self.lyric_text.insert("end", line.text + "\n")
        self.lyric_text.tag_add("center", "1.0", "end")
        self.lyric_text.config(state="disabled")
        self.lyric_idx = -1
        self._refresh_lyric()

    def _set_lyric_text(self, text):
        self.lyric_text.config(state="normal")
        self.lyric_text.delete("1.0", "end")
        self.lyric_text.insert("end", text)
        self.lyric_text.tag_add("center", "1.0", "end")
        self.lyric_text.config(state="disabled")

    def _refresh_lyric(self):
        if not self.lyrics:
            return
        sec_ms = int(self._current_sec() * 1000) + self.lyric_offset_ms
        idx = -1
        for i, line in enumerate(self.lyrics):
            if line.time_ms <= sec_ms:
                idx = i
            else:
                break
        if idx == self.lyric_idx:
            return
        self.lyric_idx = idx
        self.lyric_text.config(state="normal")
        self.lyric_text.tag_remove("cur", "1.0", "end")
        if idx >= 0:
            line_start = "%d.0" % (idx + 1)
            line_end = "%d.end" % (idx + 1)
            self.lyric_text.tag_add("cur", line_start, line_end)
            self.lyric_text.see(line_start)
        self.lyric_text.config(state="disabled")

    # ---------- 其他 ----------

    def _update_covers(self, path):
        """按当前封面模式更新封面。"""
        def worker():
            pil_img = self._load_embedded_cover(path)
            self.root.after(0, lambda: self._on_cover_loaded(path, pil_img))

        threading.Thread(target=worker, daemon=True).start()

    def _on_cover_loaded(self, path, pil_img):
        """内嵌封面读取完成（主线程）。已切歌则丢弃。"""
        if self.current_path != path:
            return
        if pil_img is not None:
            self._apply_cover_image(pil_img)
            return
        self._set_cover_placeholder()
        self._fetch_cover_async(path)

    def _load_embedded_cover(self, path):
        """读取文件内嵌封面，返回 PIL Image；无则 None。"""
        if Image is None:
            return None
        try:
            data = get_embedded_cover(path)
            if not data:
                return None
            img = Image.open(io.BytesIO(data))
            img.load()
            return img
        except Exception:
            return None

    def _apply_cover_image(self, pil_img):
        if pil_img is None:
            self._set_cover_placeholder()
            return
        small = pil_img.copy()
        small.thumbnail((56, 56))
        big = pil_img.copy()
        big.thumbnail((168, 168))
        self.cover_img_small = ImageTk.PhotoImage(small)
        self.cover_img_big = ImageTk.PhotoImage(big)
        self.cover_label.config(image=self.cover_img_small, text="")
        self.now_cover_label.config(image=self.cover_img_big, text="")

    def _set_cover_placeholder(self):
        self.cover_img_small = None
        self.cover_img_big = None
        self.cover_label.config(image="", text="♪", bg=COVER_PLACEHOLDER, fg="white",
                                font=("Microsoft YaHei UI", 18, "bold"))
        self.now_cover_label.config(image="", text="♪", bg=COVER_PLACEHOLDER, fg="white",
                                    font=("Microsoft YaHei UI", 42, "bold"))

    def _set_song_info(self, title, artist, dur=0.0):
        """同步更新中间“现在播放”的歌名/歌手。"""
        self.now_title_label.config(text=title or "未播放")
        self.now_artist_label.config(text=artist or "选择歌曲开始播放")

    def _cover_cache_path(self, title, artist):
        """联网封面的本地缓存路径。"""
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        folder = os.path.join(base, "covers_cache")
        name = re.sub(r'[\\/:*?"<>|]', "_", "%s_%s" % (artist, title))
        return os.path.join(folder, name + ".jpg")

    def _fetch_cover_async(self, path):
        """后台联网抓封面：先查本地缓存，成功后回填并落盘缓存。"""
        title, artist = self._parse_filename(path)
        cache_path = self._cover_cache_path(title, artist)

        def worker():
            data = None
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, "rb") as f:
                        data = f.read()
                except Exception:
                    data = None
            if not data:
                data = fetch_online_cover(title, artist)
                if data:
                    try:
                        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                        with open(cache_path, "wb") as f:
                            f.write(data)
                    except Exception:
                        pass
            self.root.after(0, lambda: self._apply_cover_bytes(data, path))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_cover_bytes(self, data, path):
        """联网封面回填；若已切歌则丢弃。"""
        if not data or path != self.current_path:
            return
        try:
            img = Image.open(io.BytesIO(data))
            img.load()
        except Exception:
            return
        self._apply_cover_image(img)

    def _on_space(self, event):
        if isinstance(event.widget, tk.Entry):
            return
        self._toggle_play()
        return "break"

    def _toggle_desktop_lyrics(self):
        """切换桌面悬浮歌词窗口显示/隐藏。"""
        if self.desktop_lyrics is None:
            try:
                self.desktop_lyrics = DesktopLyrics(self)
            except Exception as exc:
                messagebox.showwarning("桌面歌词", "无法创建桌面歌词窗口：\n%s" % exc)
                return
        if self.desktop_lyrics.winfo_viewable():
            self.desktop_lyrics.hide()
            self.dk_btn.config(fg="#C9CBD2", text="♪ 桌面歌词")
        else:
            self.desktop_lyrics.show()
            self.dk_btn.config(fg=self.ACCENT, text="♪ 桌面歌词·开")

    def _on_close(self):
        try:
            self._save_favs()
        except Exception:
            pass
        try:
            if self.desktop_lyrics is not None:
                self.desktop_lyrics.destroy()
        except Exception:
            pass
        try:
            for fn in os.listdir(tempfile.gettempdir()):
                if fn.startswith("mmplayer_") and fn.endswith(".wav"):
                    try:
                        os.remove(os.path.join(tempfile.gettempdir(), fn))
                    except OSError:
                        pass
        except Exception:
            pass
        try:
            if hasattr(self, "playing_title"):
                self.playing_title._stop()
            if pygame is not None:
                pygame.mixer.music.stop()
                pygame.mixer.quit()
        except Exception:
            pass
        self.root.destroy()

class DesktopLyrics(tk.Toplevel):
    """桌面悬浮歌词窗：透明底、置顶、可拖动，支持改颜色与字号。"""

    TRANS_KEY = "#010203"   # 透明色键（整色透明）

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.color = "#FFFFFF"
        self.font_size = 26
        self.always_top = True
        self._drag_off = (0, 0)
        self._last_key = None
        self._panel = None   # 自制右键面板
        self._hover = False  # 鼠标是否靠近（靠近时背景变浅蓝可操作）

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-transparentcolor", self.TRANS_KEY)
        self.configure(bg=self.TRANS_KEY)
        self.HOVER_BG = "#A8D0F0"   # 浅蓝色：鼠标靠近时的“浅透明”背景

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry("860x150+%d+%d" % (max(0, sw - 920), max(0, sh - 210)))

        self.canvas = tk.Canvas(self, width=860, height=150, bg=self.TRANS_KEY,
                                highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<Button-3>", self._on_menu)
        self.protocol("WM_DELETE_WINDOW", self.hide)

        self._refresh()
        self.after(150, self._loop)
        self.withdraw()

    _PANEL_BG = "#2C2C2E"
    _PANEL_FG = "#F2F2F2"

    def _on_menu(self, e):
        """右键弹出设置面板（歌词颜色/字体大小/背景/置顶/关闭）。"""
        self._close_panel()
        p = tk.Toplevel(self.app.root)
        p.overrideredirect(True)
        p.attributes("-topmost", True)
        p.configure(bg=self._PANEL_BG)
        self._panel = p
        self._panel_items("main")
        p.update_idletasks()
        w = p.winfo_reqwidth()
        h = p.winfo_reqheight()
        sw = p.winfo_screenwidth()
        sh = p.winfo_screenheight()
        x = min(e.x_root, sw - w - 8)
        y = min(e.y_root, sh - h - 8)
        p.geometry("+%d+%d" % (max(0, x), max(0, y)))

    def _close_panel(self):
        if self._panel is not None:
            try:
                self._panel.destroy()
            except Exception:
                pass
            self._panel = None

    def _panel_items(self, level):
        if self._panel is None:
            return
        p = self._panel
        for child in p.winfo_children():
            child.destroy()
        rows = []
        if level == "main":
            off = self.app.lyric_offset_ms
            rows = [("歌词颜色 ›", "color"),
                    ("字体大小 ›", "font"),
                    ("歌词同步 ›%s" % ("（%+.1fs）" % (off / 1000.0) if off else ""), "off"),
                    ("总在最前：%s" % ("开" if self.always_top else "关"), "top"),
                    ("关闭歌词", "close")]
        elif level == "color":
            rows = [(label, ("c", c)) for label, c in (
                ("白色", "#FFFFFF"), ("金色", "#FFD700"), ("浅绿", "#7CFC00"),
                ("粉色", "#FF69B4"), ("天蓝", "#4FC3F7"), ("橙色", "#FFA726"),
                ("红色", "#FF5252"), ("‹ 返回", "main"))]
        elif level == "font":
            rows = [("增大 (+2)", ("f", 1)), ("减小 (-2)", ("f", -1)),
                    ("‹ 返回", "main")]
        elif level == "off":
            cur = self.app.lyric_offset_ms
            rows = [("歌词提前 0.5s", ("off", -500)),
                    ("歌词延后 0.5s", ("off", 500)),
                    ("当前微调：%+.1fs" % (cur / 1000.0), None),
                    ("重置为 0", ("off", 0)),
                    ("‹ 返回", "main")]
        for text, act in rows:
            b = tk.Label(p, text=text, bg=self._PANEL_BG, fg=self._PANEL_FG,
                         font=("Microsoft YaHei UI", 10),
                         cursor=("hand2" if act is not None else "arrow"),
                         padx=14, pady=7)
            b.pack(fill="x")
            if act is not None:
                b.bind("<Button-1>", lambda _e, a=act: self._panel_action(a))
                b.bind("<Enter>", lambda _e, w=b: w.config(bg="#3A3A3C"))
                b.bind("<Leave>", lambda _e, w=b: w.config(bg=self._PANEL_BG))
        p.update_idletasks()

    def _panel_action(self, act):
        if isinstance(act, str):
            if act == "color":
                self._panel_items("color")
            elif act == "font":
                self._panel_items("font")
            elif act == "off":
                self._panel_items("off")
            elif act == "top":
                self.toggle_top()
                self._panel_items("main")
            elif act == "close":
                self.hide()
                self._close_panel()
            elif act == "main":
                self._panel_items("main")
            return
        kind, val = act
        if kind == "c":
            self.set_color(val)
            self._close_panel()
        elif kind == "f":
            self.set_font(self.font_size + val)
            self._panel_items("font")
        elif kind == "off":
            self.app.lyric_offset_ms = max(-10000, min(10000, val))
            self._panel_items("off")

    def set_color(self, c):
        self.color = c
        self._last_key = None
        self._refresh()

    def set_font(self, size):
        self.font_size = max(14, min(64, size))
        self._last_key = None
        self._refresh()

    def toggle_top(self):
        self.always_top = not self.always_top
        self.attributes("-topmost", self.always_top)

    def _check_hover(self):
        """轮询鼠标位置：靠近窗口（含外扩 12px）→ 背景变浅蓝；离开 → 恢复全透明。"""
        try:
            mx, my = self.winfo_pointerxy()
        except Exception:
            return
        x0, y0 = self.winfo_rootx(), self.winfo_rooty()
        inside = (x0 - 12 <= mx <= x0 + self.winfo_width() + 12 and
                  y0 - 12 <= my <= y0 + self.winfo_height() + 12)
        if self._panel is not None:
            inside = True
        if inside and not self._hover:
            self._hover = True
            self.canvas.config(bg=self.HOVER_BG)
            self._last_key = None
            self._refresh()
        elif not inside and self._hover:
            self._hover = False
            self.canvas.config(bg=self.TRANS_KEY)
            self._last_key = None
            self._refresh()

    def show(self):
        self.deiconify()
        self.lift()
        self.after(150, self._loop)

    def hide(self):
        self.withdraw()

    def _on_press(self, e):
        self._close_panel()
        self._drag_off = (e.x_root - self.winfo_x(), e.y_root - self.winfo_y())

    def _on_drag(self, e):
        self.geometry("+%d+%d" % (e.x_root - self._drag_off[0],
                                  e.y_root - self._drag_off[1]))

    def _loop(self):
        if self.winfo_viewable():
            self._check_hover()
            self._refresh()
            self.after(150, self._loop)

    def _refresh(self):
        app = self.app
        lyrics = app.lyrics
        idx = app.lyric_idx
        cur = lyrics[idx].text if lyrics and 0 <= idx < len(lyrics) else ""
        nxt = (lyrics[idx + 1].text if lyrics and 0 <= idx + 1 < len(lyrics) else "")
        key = (idx, self.font_size, self.color)
        if key == self._last_key:
            return
        self._last_key = key
        cv = self.canvas
        cv.delete("all")
        w = cv.winfo_width() or 860
        h = cv.winfo_height() or 150
        if not cur:
            cv.create_text(w / 2, h / 2, text="♪ 桌面歌词（播放时同步显示）",
                           fill=self.color,
                           font=("Microsoft YaHei UI", max(14, self.font_size - 8)),
                           anchor="center")
            return
        f1 = ("Microsoft YaHei UI", self.font_size, "bold")
        f2 = ("Microsoft YaHei UI", max(12, int(self.font_size * 0.72)))
        cy = int(h * 0.42) if nxt else int(h / 2)
        shadow = "#1F2A3D" if self._hover else "#333333"
        cv.create_text(w / 2 + 1, cy + 1, text=cur, fill=shadow, font=f1, anchor="center")
        cv.create_text(w / 2, cy, text=cur, fill=self.color, font=f1, anchor="center")
        if nxt:
            ny = int(h * 0.80)
            cv.create_text(w / 2 + 1, ny + 1, text=nxt, fill=shadow, font=f2, anchor="center")
            cv.create_text(w / 2, ny, text=nxt, fill="#B8B8B8", font=f2, anchor="center")


def main():
    if os.name == "nt":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        # 单实例保护：已有实例运行时直接退出，避免多窗口叠加互相拦截鼠标
        try:
            kernel32 = ctypes.windll.kernel32
            _mutex = kernel32.CreateMutexW(None, False, "Local\\AuroraMusicPlayerMutex")
            if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
                return
        except Exception:
            pass
    root = tk.Tk()
    root.title("Aurora Music · 本地播放器")
    root.overrideredirect(True)
    w, h = 1200, 780
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    x = max(0, (sw - w) // 2)
    y = max(0, (sh - h) // 2)
    root.geometry("%dx%d+%d+%d" % (w, h, x, y))
    root.minsize(980, 620)
    if os.name == "nt":
        icon = None
        if getattr(sys, "frozen", False):
            icon = os.path.join(os.path.dirname(sys.executable), "icon.ico")
        else:
            icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if icon and os.path.exists(icon):
            try:
                root.iconbitmap(icon)
            except Exception:
                pass
    app = MusicPlayerApp(root)
    # 任务栏按钮：无边框窗口默认 TOOLWINDOW（任务栏不显示）
    # → 窗口显示后再换 APPWINDOW 样式，任务栏出现按钮，最小化后可恢复
    try:
        root.update_idletasks()
        root.update()
        _hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        _ex = ctypes.windll.user32.GetWindowLongW(_hwnd, -20)
        _ex = (_ex & ~0x00000080) | 0x00040000  # 去 WS_EX_TOOLWINDOW，加 WS_EX_APPWINDOW
        ctypes.windll.user32.SetWindowLongW(_hwnd, -20, _ex)
    except Exception:
        pass
    root.mainloop()

if __name__ == "__main__":
    main()
