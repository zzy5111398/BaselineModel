#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 10:35:16 2019

@author: riteshkakade
"""


import time
from collections import deque as dq

import numpy as np

from Agents.Household import Household as hh
from Agents.FirmCons import FirmCons as fc
from Agents.FirmCap import FirmCap as fk
from Agents.Bank import Bank as b
from Agents.Govt import Govt as gov
from Agents.CentralBank import CentralBank as cb
from StatDept.Initializer import InitialValues as iv
from StatDept.StatOffice import Aggregate as so_agg


class Economy:

    def __init__(self, balance_sheet, tf_matrix, T, parameters, network):
        self.balance_sheet_agg = balance_sheet
        self.tf_matrix_agg = tf_matrix
        self.T = T
        self.param = parameters
        self.households = {}
        self.firms_cons = {}
        self.firms_cap = {}
        self.banks = {}
        self.govt = None
        self.central_bank = None

        self.u_n = parameters[4][1]
        self.i_lbar = parameters[1][1]
        self.i_dbar = parameters[1][0]

    def populate(self):
        st = time.time()
        MODEL = self.param[4]
        g_ss = MODEL[0]
        kappa = MODEL[3]
        eta = MODEL[4]

        C_r = self.param[0]
        TAX = self.param[2]
        INT = self.param[1]
        HH = self.param[5]
        FC = self.param[6]
        FK = self.param[7]
        BANK = self.param[8]
        GCB = self.param[9]

        size_h = self.param[3][0]
        size_fc = self.param[3][1]
        size_fk = self.param[3][2]
        size_b = self.param[3][3]

        Pc = FC[16]
        Pk = FK[12]
        K = MODEL[10]/size_fc

        Dh = self.balance_sheet_agg[0][0]/size_h
        HH.append(FC[20] + FK[17] + BANK[4])

        Dfc = self.balance_sheet_agg[0][1]/size_fc

        Lc = iv.get_loan(abs(self.balance_sheet_agg[1][1]/size_fc), eta, g_ss)
        Kc = iv.get_capital_batches(Pk, K, kappa, g_ss)
        cap_amort = iv.get_cap_amort(Pk, K, kappa, g_ss)
        prin_payments_c = iv.get_principal_loan_payments(Lc[0]*size_fc, eta, g_ss)
        FC.append(cap_amort*size_fc)
        FC.append(FC[18] - FC[19] + FC[21] - (FC[17]*FC[14]*g_ss/(1 + g_ss)) - prin_payments_c)

        Dfk = self.balance_sheet_agg[0][2]/size_fk
        Lk = iv.get_loan(abs(self.balance_sheet_agg[1][2]/size_fk), eta, g_ss)
        prin_payments_k = iv.get_principal_loan_payments(Lk[0]*size_fk, eta, g_ss)
        FK.append(FK[15] - FK[16] - (FC[13]*FC[11]*g_ss/(1 + g_ss)) - prin_payments_k)

        Db = abs(self.balance_sheet_agg[0][3]/size_b)
        Lb = abs(self.balance_sheet_agg[1][3]/size_b)
        Bb = abs(self.balance_sheet_agg[4][3]/size_b)
        Rb = abs(self.balance_sheet_agg[5][3]/size_b)

        for i in range(size_h):
            household = hh(Dh, HH, C_r/size_h, Pc, MODEL, INT, size_h, i)
            self.households[i] = household

        for i in range(size_fc):
            firm_cons = fc(Dfc, Lc, C_r/size_fc, Kc, FC, MODEL,
                           Pk, FK[14], INT, size_fc, i)
            self.firms_cons[10000 + i] = firm_cons

        for i in range(size_fk):
            firm_cap = fk(Dfk, Lk, FK, MODEL, INT, size_fk, i)
            self.firms_cap[20000 + i] = firm_cap

        for i in range(size_b):
            bank = b(Db, Lb, Bb, Rb, BANK, INT, MODEL, TAX[1], size_b, i)
            self.banks[30000 + i] = bank

        UN = int(size_h - (FC[0] + FK[0] + GCB[0]))
        GCB.append(UN)
        GCB.append(HH[7] + FC[19] + FK[16] + (self.banks[30000].T)*size_b)

        self.govt = gov(abs(self.balance_sheet_agg[4][4]),
                        GCB, TAX, MODEL, INT)
        self.central_bank = cb(abs(self.balance_sheet_agg[4][5]),
                               abs(self.balance_sheet_agg[5][5]),
                               GCB, INT, MODEL)

        print("Population created in %f seconds" % (time.time()-st))

    def create_network(self, network):
        st = time.time()
        self.create_labor_network(network[0], network[1], network[2])
        self.create_deposit_network(network[3])
        self.create_credit_network(network[4])
        self.create_capital_network(network[5])

        omega = self.govt.omega
        tau = self.govt.tau_h
        g = 1 + self.param[4][0]
        for h in self.households.values():
            if h.u_h > 0:
                h.dole = omega*h.w_bar
                h.T = tau*((h.int_D + h.div)/g)
                h.NI = h.dole + (h.int_D + h.div)/g - h.T
            else:
                h.T = tau*(h.w + (h.int_D + h.div)/g)
                h.NI = h.w + (h.int_D + h.div)/g - h.T

        print("Network created in %f seconds" % (time.time()-st))

    def create_labor_network(self, N1, N2, N3):
        for n1 in range(len(N1)):
            f = self.getObjectById(10000 + n1)
            for h1 in N1[n1]:
                f.id_workers.add(h1)
                h = self.getObjectById(h1)
                h.id_firm = 10000 + n1
                h.w = self.param[4][2]
                h.u_h = 0

        for n2 in range(len(N2)):
            f = self.getObjectById(20000 + n2)
            for h1 in N2[n2]:
                f.id_workers.add(h1)
                h = self.getObjectById(h1)
                h.id_firm = 10000 + n2
                h.w = self.param[4][2]
                h.u_h = 0

        for n3 in N3:
            self.govt.id_workers.add(n3)
            h = self.getObjectById(n3)
            h.id_firm = -1
            h.w = self.param[4][2]
            h.u_h = 0

    def create_deposit_network(self, BD):
        for i in range(len(BD)):
            b = self.getObjectById(30000 + i)
            for d in BD[i]:
                b.id_depositors.add(d)
                dp = self.getObjectById(d)
                dp.id_bank_d = 30000 + i

    def create_credit_network(self, BC):
        for i in range(len(BC)):
            b = self.getObjectById(30000 + i)
            for d in BC[i]:
                b.id_debtors.add(d)
                ln = self.getObjectById(d)
                ln.id_bank_l = dq([30000 + i]*20, maxlen=20)

    def create_capital_network(self, KC):
        for i in range(len(KC)):
            for k in KC[i]:
                fc = self.getObjectById(k)
                fc.id_firm_cap = 20000 + i

    def getObjectById(self, id_):
        # flag is 0, 1, 2, 3 for households, firm_cons,
        # firm_cap and banks respectively
        flag = id_//10000
        if flag == 0:
            return self.households[id_]
        elif flag == 1:
            return self.firms_cons[id_]
        elif flag == 2:
            return self.firms_cap[id_]
        elif flag == 3:
            return self.banks[id_]
        else:
            print("Enter the valid flag: 0, 1, 2 or 3")
            return None

    def get_agents_dict(self):
        return [self.households, self.firms_cons, self.firms_cap,
                self.banks, self.govt, self.central_bank]

    def get_aggregate_bal_sheet(self, isT0=False):
        agents_dict = self.get_agents_dict()
        self.balance_sheet_agg = so_agg.get_balance_sheet(agents_dict, isT0)
        return self.balance_sheet_agg

    def form_expectation(self):
        for h in self.households.values():
            h.form_expectations()

        for f_c in self.firms_cons.values():
            f_c.form_expectations()

        for f_k in self.firms_cap.values():
            f_k.form_expectations()

    def production_labor_prices(self):
        for f_c in self.firms_cons.values():
            f_c.calc_desired_output()
            f_c.calc_labor_demand()
            f_c.set_price()

        for f_k in self.firms_cap.values():
            f_k.calc_desired_output()
            f_k.calc_labor_demand()
            f_k.set_price()

    def household_revise_wages(self):
        for h in self.households.values():
            h.revise_wage(self.u_n)

    def set_interest_rates(self):
        for bk in self.banks.values():
            bk.set_interest_rates(self.i_dbar, self.i_lbar,
                                  self.central_bank.LR, self.central_bank.CR)

    def calc_investment_demand(self):
        for f_c in self.firms_cons.values():
            f_c.calc_real_inv_demand()

    def get_aggregate_tf_matrix(self):
        agents_dict = self.get_agents_dict()
        self.tf_matrix_agg = so_agg.get_tf_matrix(agents_dict)
        return self.tf_matrix_agg
