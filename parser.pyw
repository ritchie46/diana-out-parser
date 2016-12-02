import re
import csv
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import os
from PyQt4.QtGui import *
import sys
from PyQt4 import QtCore, QtGui
import time


class OutParser:
    def __init__(self, path=None):
        import os
        for filename in os.listdir(os.getcwd()):
            if filename[-4:] == ".out":
                path = os.path.join(os.getcwd(), filename)
                break
        self.out_file = path

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

    def _parse_out_file(self):
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
        with open(self.out_file) as f:
            out = f.read()
            print("reading out file")
            while len(out) > 0:
                indx = out.find("INITIATED:")  # Get index of the next step via 'INITIATED"
                if indx > 0:
                    # Get the load step
                    query = re.search(r"\d+", out[indx - 7: indx + 2])
                    if query:
                        step = int(query.group(0))
                        self.load_steps.append(step)

                    # Slice file index is now zero'
                    out = out[indx:]

                    # Get the load combination
                    query = re.search(r"(\d\d|\d)", out[31: 42])
                    if query:
                        combi_nr = int(query.group(0))
                        self.load_numbers.append(combi_nr)

                    # Get the load factor
                    indx = out.find("TOTAL LOAD FACTOR:")
                    query = re.search(r"\d[.]\d\d\d[E][-]\d\d|\d[.]\d\d\d[E][+]\d\d", out[indx: indx + 70])
                    if query:
                        lf = float(query.group(0))
                        self.load_factors.append(lf)

                    query = re.search(r"\d[.]\d\d\d[E][-]\d\d|\d[.]\d\d\d[E][+]\d\d", out[:60])
                    if query:
                        ld_increment = float(query.group(0))
                        self.load_increments.append(ld_increment)

                    # Convergence check
                    indx = out.find("TERMINATED")
                    query = re.search(r"\bNO\b", out[indx: indx + 25])
                    if query:
                        self.convergence.append(False)
                    else:
                        self.convergence.append(True)

                    # Iterations
                    query = re.search("\d+", out[indx: indx + 40])
                    if query:
                        self.iterations.append(int(query.group(0)))

                    # Energy convergence
                    substr = out[indx - 250: indx]
                    indx = substr.rfind("RELATIVE ENERGY VARIATION")
                    query = re.search("\d.\d+[E].\d+", substr[indx: indx + 50])
                    if query:
                        self.energy_conv.append(float(query.group(0)))

                    # Out of balace force
                    indx = substr.rfind("RELATIVE OUT OF BALANCE FORCE")
                    query = re.search("\d.\d+[E].\d+", substr[indx: indx + 50])
                    if query:
                        self.force_conv.append(float(query.group(0)))

                    # Displacement variation
                    indx = substr.rfind("RELATIVE DISPLACEMENT VARIATION")
                    query = re.search("\d.\d+[E].\d+", substr[indx: indx + 50])
                    if query:
                        self.displ_conv.append(float(query.group(0)))

                    # Plasticity model
                    indx = out.find("PLASTICITY LOGGING SUMMARY")
                    query = re.findall(r"\d+", out[indx: indx + 192])
                    if query:
                        self.plast_columns.append(list(map(float, query)))

                    # Cracks model
                    indx = out.find("CRACKING LOGGING SUMMARY")
                    query = re.findall(r"\d+", out[indx: indx + 238])
                    if query:
                        self.crack_columns.append(list(map(float, query)))

                    # Cumulative Reaction
                    indx = out.find("CUMULATIVE REACTION")
                    query = re.findall(r"\S+\d+[A-Z]+\S+\d", out[indx: indx + 145])
                    if query:
                        self.force_sum.append(list(map(lambda x: float(x.replace("D", "E")), query)))

                    out = out[10:]  # trim part before 'INITIATED:'
                else:
                    break

    def plot(self):
        gs = gridspec.GridSpec(2, 2)
        x_val = self.load_steps
        fig = plt.figure()
        plt.style.use("seaborn-whitegrid")
        ax = fig.add_subplot(gs[0, -1:])
        ax.set_ylabel("numerical deviation")
        ax.set_xlabel("load steps")

        a = ax.twinx()
        try:
            a.step(x_val, self.iterations, color="g", label="iterations")
        except ValueError:
            return 1

        a.set_ylim(0, max(self.iterations) + 10)
        a.set_ylabel("iterations")

        try:
            if len(self.energy_conv) > 0:
                ax.plot(x_val, self.energy_conv, label="energy")
            if len(self.force_conv) > 0:
                ax.plot(x_val, self.force_conv, label="force")
            if len(self.displ_conv) >0:
                ax.plot(x_val, self.displ_conv, label="displacement")
        except ValueError:
            return 1

        ax.legend(loc=2)
        a.legend(loc=4)

        # second plot
        ax = fig.add_subplot(gs[1, -1:])
        ax.plot(x_val, list(map(lambda x: x[0], self.crack_columns)), label="cracks")
        ax.plot(x_val, list(map(lambda x: x[0], self.plast_columns)), label="plasticity")
        ax.set_xlabel("load steps")
        ax.legend(loc=2)

        # third plot
        ax = fig.add_subplot(gs[0:, 0])

        try:
            ax.plot(x_val, list(map(lambda x: x[0] / 1000, self.force_sum)), label="force x")
            ax.plot(x_val, list(map(lambda x: x[1] / 1000, self.force_sum)), label="force y")
            ax.plot(x_val, list(map(lambda x: x[2] / 1000, self.force_sum)), label="force z")
        except ValueError:
            return 1

        ax.set_ylabel("force [kN]")
        ax.set_xlabel("load steps")
        ax.legend(loc=1)
        f = os.getcwd() + "\\live.png"
        plt.tight_layout()
        fig.savefig(f, dpi=300)

    def to_csv(self):
        os.makedirs("parsed_csv", exist_ok=True)

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
            self.force_sum,
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
            "sum_forces"
        ]

        for i in range(len(files)):
            if len(files[i]) > 0:
                if type(files[i][0]) != list:
                    try:
                        with open("parsed_csv/%s.csv" % names[i], 'w') as f:
                            write = csv.writer(f)
                            write.writerow(files[i])
                    except PermissionError:
                        pass

class MyThread(QtCore.QThread):
    def run(self):
        # make thread sleep to make sure
        # QApplication is running before doing something
        time.sleep(2)
        self.loop()

    def loop(self):
        while 1:
            time.sleep(60)
            self.emit(QtCore.SIGNAL("update()"))


class MySignal(QtCore.QObject):
    sig = QtCore.pyqtSignal(list)
    sigStr = QtCore.pyqtSignal(str)


class ImgUi(QtGui.QMainWindow):
    def __init__(self):
        super().__init__()
        self.padding = 30
        self.img_w = 768
        self.img_h = 567
        self.setGeometry(300, 300, self.img_w + self.padding * 2, self.img_h + self.padding * 2)
        self.setWindowTitle('diana live')

        # text label
        self.l1 = QLabel(self)
        self.l1.setText("Data is being queried")
        self.l1.setAlignment(QtCore.Qt.AlignCenter)
        self.l1.setGeometry(0, 0, self.img_w, self.padding)

        self.label = QLabel(self)
        self.label.setScaledContents(True)
        pixmap = QPixmap(os.getcwd() + "/live.png")

        self.label.setPixmap(pixmap)
        self.label.setGeometry(self.padding, self.padding, self.img_w, self.img_h)
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.l1)
        self.layout.addWidget(self.label)
        thread = MyThread(self)
        self.connect(thread, QtCore.SIGNAL("update()"), self.update)
        thread.start()

    def update(self):
        try:
            a._parse_out_file()
            a.to_csv()
            a.plot()
        except:
            print("An exception occured.")
        self.l1.setText("Current load step: %d" % a.load_steps[-1])
        self.label.setPixmap(QPixmap(os.getcwd() + "/live.png"))


if __name__ == "__main__":
    a = OutParser()
    # a._parse_out_file()
    # a.to_csv()
    # a.plot()



    """
    print("Load factors\n", a.load_factors, "\nIncrements\n", a.load_increments, "\nsteps\n", a.load_steps,
          "\nload number\n", a.load_numbers, "\nConvergence\n", a.convergence, "\nplasticity\n", a.plast_columns,
          "\ncracks\n", a.crack_columns, "\ncumulative force\n", a.force_sum, "\niterations\n", a.iterations,
          "\nenergy_conv\n", a.energy_conv, "\ndispl_conv\n", a.displ_conv, "\nforce_conv\n", a.force_conv)
    """

    app = QtGui.QApplication(sys.argv)
    window = ImgUi()
    window.show()
    sys.exit(app.exec_())





