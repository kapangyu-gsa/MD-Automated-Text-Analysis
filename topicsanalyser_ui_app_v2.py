import sys
import pandas as pd
from PyQt5.QtCore import QRegExp, Qt
from PyQt5.QtGui import QRegExpValidator
from textfilereader import TextFileReader
from topicsanalyser import TopicsAnalyser
from topics_modeling_wizard import Ui_TopicsModelingWizard
from mylogging.logging import MyLogging
from mylogging.exception_formats import system_hook_format
from PyQt5.QtWidgets import (
    QWizard,
    QWizardPage,
    QApplication, 
    QFileDialog, 
    QErrorMessage,
    QMessageBox
)

class TopicsAnalyser_UI(QWizard):
    def __init__(self, parent=None):
        super(TopicsAnalyser_UI, self).__init__(parent)
        self.ui = Ui_TopicsModelingWizard()
        self.ui.setupUi(self)
        self.msg = QMessageBox()
        
        # register the fields to make them required
        self.ui.DataFilePage.registerField('data_file_txt*', self.ui.data_file_txt)
        self.ui.DataFilePage.registerField('text_col_name_txt*', self.ui.text_col_name_txt)
        
        # override some default page functions
        self.ui.DataFilePage.validatePage = self.validate_data_file_page        
        self.ui.TopicsModelingPage.initializePage = self.init_modeling_page
        
        # link the signals to the slots
        self.ui.browse_btn.clicked.connect(self.getfile)     
        self.ui.run_btn.clicked.connect(self.run_topics_analyser)
        self.ui.add_col_btn.clicked.connect(self.add_other_col_for_import)
        self.ui.remove_col_btn.clicked.connect(self.remove_other_col_for_import)
        
        # initialize the data for analysis 
        self.data_reader = TextFileReader('')
        
        # set up logger
        self.logger = MyLogging('TopicsAnalyser_UI').logger
               
        # set up the uncaught exceptions handler
        sys.excepthook = self.uncaught_exceptions_hander
                
    def run_topics_analyser(self):        
        if (self.ui.output_file_name_txt.text() == ''):
            self.show_message(['Please enter the output file name.'], icon=QMessageBox.Warning)
            return
            
        get_wordlist = lambda text: [word.strip() for word in text.split(',')] if (len(text) > 0) else []        
        addl_stopwords = get_wordlist(self.ui.addl_stopwords_txt.text())       
        groupby_cols = [ self.ui.groupby_cols_lst.item(i).text() for i in range(self.ui.groupby_cols_lst.count()) if self.ui.groupby_cols_lst.item(i).checkState() == Qt.Checked]
        
        data = self.data_reader.get_dataframe(self.ui.text_col_name_txt.text(), groupby_cols)
        analyser = TopicsAnalyser(data, self.ui.output_file_name_txt.text())
        message = analyser.get_topics(self.ui.num_topics_spb.value(), groupby_cols, self.ui.num_ngrams_spb.value(), addl_stopwords)
            
        self.show_message([message], icon=QMessageBox.Information)
        
        
    def getfile(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Excel files (*.xlsx)", options=options) 
        if (filename):
            self.ui.data_file_txt.setText(filename)
            
            
    def validate_data_file_page(self):
        isvalid = True
        errors = []
        # validate the names of the text column and the additional columns
        self.data_reader.data_file_path = self.ui.data_file_txt.text()
        self.data_reader.read_data()
        
        text_col = self.ui.text_col_name_txt.text()
        cols = [text_col] + [self.ui.other_cols_lst.item(i).text() for i in range(self.ui.other_cols_lst.count())]
        cols_not_exist = self.data_reader.verify_columns_exist(cols)
        if (len(cols_not_exist) > 0):
            errors.extend(['- The following column(s) do not exist in the data file: '] + cols_not_exist)
            isvalid = False
        
        if (self.data_reader.is_text_column(text_col) == False):
            errors.extend([f'\n\n- "{text_col}" is not a text column.'])
            isvalid = False
        
        if (len(errors) > 0):
            self.show_message(errors)
            
        return isvalid
    
    
    def init_modeling_page(self):
        # copy the other column names for grouping use
        self.copy_other_col_names()
                   
        
    def show_message(self, msgs: list, buttons_shown: int= QMessageBox.Ok, icon: int= QMessageBox.Critical):
        self.msg.setIcon(icon)
        self.msg.setText(('').join(msgs))
        self.msg.setStandardButtons(buttons_shown)
        self.msg.exec()
        
        
    def copy_other_col_names(self):
        self.ui.groupby_cols_lst.clear()
        for i in range(self.ui.other_cols_lst.count()):
            item = self.ui.other_cols_lst.item(i).clone()
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.ui.groupby_cols_lst.addItem(item)
        
    
    def add_other_col_for_import(self):
        other_col = self.ui.other_col_txt.text()
        if (other_col != ''):
            cols_existed = self.ui.other_cols_lst.findItems(other_col, Qt.MatchCaseSensitive)
            if (len(cols_existed) > 0):
                self.show_message([f'Column "{other_col}" was already added.'], icon=QMessageBox.Warning)
                return
            
            self.ui.other_cols_lst.addItem(other_col)
            self.ui.other_col_txt.setText('')
    
    
    def remove_other_col_for_import(self):
        if (self.ui.other_cols_lst.currentRow() != -1):
            self.ui.other_cols_lst.takeItem(self.ui.other_cols_lst.currentRow())
        
    def uncaught_exceptions_hander(self, type, value, traceback):
        log_msg = system_hook_format(type, value, traceback)
        self.logger.exception(log_msg)
        
        msg = "An unexpected error occurred below -\n" \
                f"Type: {type}\n" \
                f"Value: {value}\n\n" \
                "The error has been logged for investigation."
        self.show_message(msg)
        
        
app = QApplication(sys.argv)
window = TopicsAnalyser_UI()
window.show()
sys.exit(app.exec_())

        