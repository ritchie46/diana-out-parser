import re
import csv
import matplotlib.pyplot as plt
import matplotlib
import matplotlib.gridspec as gridspec
import os
import sys
from PyQt4 import QtCore, QtGui
import time


class OutParser:
    def __init__(self, path=None):
        """
        :param path: Path of the directory.
        """
        self.dir = path
        self.out_file = None

        # read from the out file
        self.load_steps = None
        self.load_factors = None
        self.load_numbers = None
        self.load_increments = None
        self.convergence = None
        self.iterations = None
        self.energy_conv = None
        self.displ_conv = None
        self.force_conv = None

        # plasticity columns
        """
        1. PLAST, 2. PRV. PL, 3. CRITIC, 4. PLAST NEW, 5. PRV.PL NEW, 6. CRITIC NEW
        """
        self.plast_columns = None

        # crack columns
        """
        1. CRACK,     2. OPEN,   3. CLOSED,   4. ACTIVE,   5. INACTI,   6. ARISES, 7. RE-OPENS,   8. CLOSES
        """
        self.crack_columns = None

        # cumulative reaction columns
        """
        FORCE X        FORCE Y          FORCE Z
        """
        self.force_sum = None
        self.moment_sum = None

    def parse_out_file(self):
        if self.out_file is None:
            for filename in os.listdir(self.dir):
                if filename[-4:] == ".out":
                    self.out_file = os.path.join(self.dir, filename)
                    break

        self.load_steps = []
        self.load_factors = []
        self.load_numbers = []
        self.load_increments = []
        self.convergence = []
        self.iterations = []
        self.energy_conv = []
        self.displ_conv = []
        self.force_conv = []
        self.plast_columns = []
        self.crack_columns = []
        self.force_sum = []
        self.moment_sum = []

        with open(self.out_file) as f:
            out = f.read()
            print("reading out file")
            while len(out) > 0:
                """
                Initiated blocks are not always terminated. To get closing blocks check if the initiated block is
                terminated before the next block is initiated.
                """

                ini = out.find("INITIATED:")  # Get index of the next step via 'INITIATED"
                term = out.find("TERMINATED")
                ini_2 = ini + 10 + out[ini + 10:].find("INITIATED:")

                # Check if the load step is terminated before the nex load step is initiated.
                if ini < term < ini_2:
                    # Get the load step
                    query = re.search(r"\d+", out[ini - 7: ini + 2])
                    if query:
                        step = int(query.group(0))
                        self.load_steps.append(step)
                    else:
                        self.load_steps.append(0)
                    # Slice file index is now zero'
                    out = out[ini:]

                    # Get the load combination
                    query = re.search(r"(\d\d|\d)", out[31: 42])
                    if query:
                        combi_nr = int(query.group(0))
                        self.load_numbers.append(combi_nr)
                    else:
                        self.load_numbers.append(None)

                    # Get the load factor
                    ini = out.find("TOTAL LOAD FACTOR:")
                    query = re.search(r"\d[.]\d\d\d[E][-]\d\d|\d[.]\d\d\d[E][+]\d\d", out[ini: ini + 70])
                    if query:
                        lf = float(query.group(0))
                        self.load_factors.append(lf)
                    else:
                        self.load_factors.append(None)

                    query = re.search(r"\d[.]\d\d\d[E][-]\d\d|\d[.]\d\d\d[E][+]\d\d", out[:60])
                    if query:
                        ld_increment = float(query.group(0))
                        self.load_increments.append(ld_increment)
                    else:
                        self.load_increments.append(None)

                    # Convergence check
                    ini = out.find("TERMINATED")
                    query = re.search(r"\bNO\b", out[ini: ini + 25])
                    if query:
                        self.convergence.append(False)
                    else:
                        self.convergence.append(True)

                    # Iterations
                    query = re.search("\d+", out[ini: ini + 40])
                    if query:
                        self.iterations.append(int(query.group(0)))
                    else:
                        self.iterations.append(0)

                    # Energy convergence
                    substr = out[ini - 250: ini]
                    ini = substr.rfind("RELATIVE ENERGY VARIATION")
                    query = re.search("\d.\d+[E].\d+", substr[ini: ini + 50])
                    if query:
                        self.energy_conv.append(float(query.group(0)))
                    else:
                        self.energy_conv.append(0)

                    # Out of balace force
                    ini = substr.rfind("RELATIVE OUT OF BALANCE FORCE")
                    query = re.search("\d.\d+[E].\d+", substr[ini: ini + 50])
                    if query:
                        self.force_conv.append(float(query.group(0)))
                    else:
                        self.force_conv.append(0)

                    # Displacement variation
                    ini = substr.rfind("RELATIVE DISPLACEMENT VARIATION")
                    query = re.search("\d.\d+[E].\d+", substr[ini: ini + 50])
                    if query:
                        self.displ_conv.append(float(query.group(0)))
                    else:
                        self.displ_conv.append(0)

                    # Plasticity model
                    ini = out.find("PLASTICITY LOGGING SUMMARY")
                    query = re.findall(r"\d+", out[ini: ini + 192])
                    if query:
                        self.plast_columns.append(list(map(float, query)))
                    else:
                        self.plast_columns.append((0,))

                    # Cracks model
                    ini = out.find("CRACKING LOGGING SUMMARY")
                    query = re.findall(r"\d+", out[ini: ini + 238])
                    if query:
                        self.crack_columns.append(list(map(float, query)))
                    else:
                        self.crack_columns.append((0,))

                    # Cumulative Reaction
                    ini = out.find("CUMULATIVE REACTION")
                    query = re.findall(r"\S+\d+[A-Z]+\S+\d", out[ini: ini + 145])
                    if query:
                        self.force_sum.append(list(map(lambda x: float(x.replace("D", "E")), query)))
                    else:
                        self.force_sum.append((0, 0, 0))

                    ini = out.find("MOMENT X")
                    query = re.findall(r"\S+\d+[A-Z]+\S+\d", out[ini: ini + 145])
                    if query:
                        self.moment_sum.append(list(map(lambda x: float(x.replace("D", "E")), query)))
                    else:
                        self.moment_sum.append((0, 0, 0))

                    out = out[term + 12:]  # trim 'TERMINATED'

                else:
                    out = out[ini_2:]

    def plot(self):
        gs = gridspec.GridSpec(4, 2)
        matplotlib.rcParams['xtick.labelsize'] = matplotlib.rcParams['ytick.labelsize'] = 8
        x_val = list(range(1, len(self.load_steps) + 1))
        fig = plt.figure()
        plt.style.use("seaborn-whitegrid")

        # conversion
        ax = fig.add_subplot(gs[0, -1])
        ax.set_ylabel("numerical deviation", fontsize=8)
        ax.set_xlabel("load steps", fontsize=8)
        ax.set_ylim(0, 0.1)

        try:
            if len(self.energy_conv) > 0:
                sol = equal_length(x_val, self.energy_conv)
                ax.plot(sol[0], sol[1], label="energy")
            if len(self.force_conv) > 0:
                sol = equal_length(x_val, self.force_conv)
                ax.plot(sol[0], sol[1], label="force")
            if len(self.displ_conv) > 0:
                sol = equal_length(x_val, self.displ_conv)
                ax.plot(sol[0], sol[1], label="displacement")
        except ValueError:
            print("Plot 2 not succeeded")
            plt.close(fig)
            return 1

        ax.legend(loc=2, fontsize=8)

        ax = fig.add_subplot(gs[1, -1])

        sol = equal_length(x_val, self.iterations)
        try:
            ax.step(sol[0], sol[1], color="g", label="iterations")
        except ValueError:
            print("Plot 1 not succeeded")
            plt.close(fig)
            return 1

        ax.legend(fontsize=8)
        ax.set_ylabel("iterations", fontsize=8)

        # cracks
        ax = fig.add_subplot(gs[2, -1])
        sol = equal_length(x_val, list(map(lambda x: x[0], self.crack_columns)))
        ax.plot(sol[0], sol[1], label="cracks")
        ax.set_xlabel("load steps", fontsize=8)
        ax.set_ylabel("cracks", fontsize=8)

        # cumulative forces
        sol = equal_length(x_val, self.force_sum)
        # third plot
        ax = fig.add_subplot(gs[0, 0])

        try:
            ax.plot(sol[0], list(map(lambda x: x[2] / 1000, sol[1])), label="force z", color='r')
        except ValueError:
            print("Plot 3 not succeeded")
            plt.close(fig)
            return 1
        ax.set_ylabel("force [kN]", fontsize=8)
        ax.set_xlabel("load steps", fontsize=8)
        ax.legend(loc=1, fontsize=8)

        ax = fig.add_subplot(gs[1, 0])
        try:
            ax.plot(sol[0], list(map(lambda x: x[0] / 1000, sol[1])), label="force x", color='g')
        except ValueError:
            print("Plot 4 not succeeded")
            plt.close(fig)
            return 1

        ax.set_ylabel("force [kN]", fontsize=8)
        ax.set_xlabel("load steps", fontsize=8)
        ax.legend(loc=1, fontsize=8)

        ax = fig.add_subplot(gs[2, 0])
        try:
            ax.plot(sol[0], list(map(lambda x: x[1] / 1000, sol[1])), label="force y")
        except ValueError:
            print("Plot 5 not succeeded")
            plt.close(fig)
            return 1
        ax.set_ylabel("force [kN]", fontsize=8)
        ax.set_xlabel("load steps", fontsize=8)
        ax.legend(loc=1, fontsize=8)

        # plasticity
        # fourth plot
        ax = fig.add_subplot(gs[3, 0])
        sol = equal_length(x_val, list(map(lambda x: x[0], self.plast_columns)))
        ax.plot(sol[0], sol[1])
        ax.set_xlabel("load steps", fontsize=8)
        ax.set_ylabel("plasticity", fontsize=8)
        ax.legend(loc=2, fontsize=8)

        if len(self.moment_sum) > 0:
            # cumulative moments
            sol = equal_length(x_val, self.moment_sum)

            # fifth plot
            ax = fig.add_subplot(gs[3, 1])
            try:
                ax.plot(sol[0], list(map(lambda x: x[0] / 1000, sol[1])), label="moment x", color='r')
            except ValueError:
                print("Plot 4 not succeeded")
                plt.close(fig)
                return 1
            try:
                ax.plot(sol[0], list(map(lambda x: x[1] / 1000, sol[1])), label="moment y", color='b')
            except ValueError:
                print("Plot 4 not succeeded")
                plt.close(fig)
                return 1
            try:
                ax.plot(sol[0], list(map(lambda x: x[2] / 1000, sol[1])), label="moment z", color='g')
            except ValueError:
                print("Plot 3 not succeeded")
                plt.close(fig)
                return 1

            ax.set_ylabel("moment [kNm]", fontsize=8)
            ax.set_xlabel("load steps", fontsize=8)
            ax.legend(loc=1, fontsize=8)

        f = self.dir + "\\live.png"
        plt.tight_layout()
        fig.savefig(f, dpi=300)
        plt.close(fig)
        return f

    def to_csv(self):
        os.makedirs(self.dir + "/parsed_csv", exist_ok=True)

        files = [
            self.load_steps,
            self.load_factors,
            self.load_numbers,
            self.load_increments,
            self.convergence,
            self.iterations,
            self.energy_conv,
            self.displ_conv,
            self.force_conv,
            self.plast_columns,
            self.crack_columns,

        ]
        names = [
            "load_steps",
            "load_factors",
            "load_numbers",
            "load_increments",
            "convergence",
            "iterations",
            "energy_convergence",
            "displacement_convergence",
            "force_convergence",
            "plasticity",
            "cracks",
        ]

        for i in range(len(files)):
            if len(files[i]) > 0:
                if type(files[i][0]) != list:
                    try:
                        with open("%s/parsed_csv/%s.csv" % (self.dir, names[i]), 'w') as f:
                            write = csv.writer(f)
                            write.writerow(files[i])
                    except PermissionError:
                        pass
        # sum forces

        x = []
        y = []
        z = []

        for i in range(len(self.force_sum)):
            x.append(self.force_sum[i][0])
            y.append(self.force_sum[i][1])
            z.append(self.force_sum[i][2])
        files = [x, y, z]
        names = [
            "sum_forces_x",
            "sum_forces_y",
            "sum_forces_z"
        ]
        for i in range(3):
            try:
                with open("%s/parsed_csv/%s.csv" % (self.dir, names[i]), 'w') as f:
                    write = csv.writer(f)
                    write.writerow(files[i])
            except PermissionError:
                pass


def equal_length(a, b):
    if len(a) == len(b):
        return a, b
    elif len(a) < len(b):
        short = a
    else:
        short = b

    a_new = []
    b_new = []
    for i in range(len(short)):
        a_new.append(a[i])
        b_new.append(b[i])
    return a_new, b_new


class MyThread(QtCore.QThread):
    def run(self):
        # make thread sleep to make sure
        # QApplication is running before doing something
        time.sleep(1)
        self.loop()

    def loop(self):
        while 1:
            self.emit(QtCore.SIGNAL("update()"))
            time.sleep(15)


class MySignal(QtCore.QObject):
    sig = QtCore.pyqtSignal(list)
    sigStr = QtCore.pyqtSignal(str)


class ImgUi(QtGui.QMainWindow):
    def __init__(self):
        super().__init__()
        try:
            os.remove(a.dir + "/live.png")
        except FileNotFoundError:
            pass
        self.padding = 30
        self.img_w = 768
        self.img_h = 768
        self.setGeometry(300, 300, self.img_w + self.padding * 2, self.img_h + self.padding * 2)
        self.setWindowTitle('diana live')

        # text label
        self.l1 = QtGui.QLabel(self)

        self.l1.setText("Data is being queried. args: %s" % sys.argv)
        self.l1.setAlignment(QtCore.Qt.AlignCenter)
        self.l1.setGeometry(0, 0, self.img_w, self.padding)

        self.label = QtGui.QLabel(self)
        self.label.setScaledContents(True)

        self.label.setGeometry(self.padding, self.padding, self.img_w, self.img_h)
        self.layout = QtGui.QVBoxLayout(self)
        self.layout.addWidget(self.l1)
        self.layout.addWidget(self.label)
        thread = MyThread(self)
        self.connect(thread, QtCore.SIGNAL("update()"), self.update)
        thread.start()

    def update(self):
        a.parse_out_file()
        a.to_csv()
        a.plot()

        self.l1.setText("Current load step: %d" % a.load_steps[-1])
        self.label.setPixmap(QtGui.QPixmap(a.dir + "/live.png"))


if __name__ == "__main__":
    # if len(sys.argv) > 1:
    #     a = OutParser(sys.argv[1])
    # if len(sys.argv) == 3:
    #     a.out_file = sys.argv[2]
    # else:
    #     a = OutParser(os.getcwd())

    a = OutParser(os.getcwd())
    a.out_file = os.path.join(os.getcwd(), "niras.out")

    app = QtGui.QApplication(sys.argv)
    window = ImgUi()
    window.show()
    sys.exit(app.exec_())



