##########################################################################################
# 
# Wavechild670 v0.1 
# 
# wdfgenerator.py
# 
# By Peter Raffensperger 10 July 2012
# 
# Reference:
# Toward a Wave Digital Filter Model of the Fairchild 670 Limiter, Raffensperger, P. A., (2012). 
# Proc. of the 15th International Conference on Digital Audio Effects (DAFx-12), 
# York, UK, September 17-21, 2012.
# 
# Note:
# Fairchild (R) a registered trademark of Avid Technology, Inc., which is in no way associated or 
# affiliated with the author.
# 
# License:
# Wavechild670 is licensed under the GNU GPL v2 license. If you use this
# software in an academic context, we would appreciate it if you referenced the original
# paper.
# 
##########################################################################################
"""
Wave digital filter code generator
Peter Raffensperger
2012

Rules: 
- Two components are connected by feeding one's a into the other's b and vice versa
- Two components that are connected must have the same value of R
- The connected components form a directed binary connection tree. Start computation of the 'b's at 
  the leaves and then work to the trunk. Then compute the other way to calculate the 'a's.
- If you have a non-linear element, you have to put it at the trunk of the tree.

References:
A. Fettweis, "Wave Digital Filters: Theory and Practice,"
Proc. of the IEEE, Vol. 74, No. 2, pp. 270-327, 1986.

"""

import re
import datetime
import math

class Generator():
	def __init__(self, circuitName):
		self.circuitName = circuitName
		self.code = ''
		self.RCode = ''
		self.RValues = {}
		self.RParameters = {}
		self.stateVariables = []
		
		self.inputs = []
		self.output = ''
		self.logIndentationLevel = 0
		self.headerCommentBlock = ''
		self.destructor = ''
		self.constructorList = ''
		self.constructedItems = {}
		self.extraMembers = {}
		
		self.intermediateVariables = []
	
	def RCheck(self, code):
		self.RCode += '\t\t' + code + ';\n'
	
	def HeaderCommentBlock(self, comment):
		self.headerCommentBlock += comment
	
	def ConstructorItem(self, name, code, type, parameter, reference=False):
		self.extraMembers[name] = type
		self.constructorList += code
		if reference:
			type += '&'
		self.constructedItems[parameter] = type
		
	
	def RValue(self, name, code, parameter=None, intermediate=False, type="Real"):
		print "R VALUE:", name
		print "  CODE:", code
		if not intermediate:
			self.RValues[name] = type
		if parameter is not None:
			self.RParameters[parameter] = type
			print "  PARAMETER:", type + parameter
		if not intermediate:
			self.RCode += '\t\t' + code + ';\n'
		else:
			self.RCode += '\t\tReal ' + code + ';\n'
			lhs = re.split(' =|\.|\-\>', code)[0]
			self.intermediateVariables.append(lhs)
	def Input(self, input):
		print "INPUT:", input
		self.inputs.append(input)
	def Output(self, code):
		self.output = '\t\treturn ' + code + ';\n'
	def Destructor(self, code):
		self.destructor = code
	def StateVariable(self, name):
		self.Log(name, banner="STATE VARIABLE")
		self.stateVariables.append(name)
	def AddBareCode(self, code):
		self.Log(code, banner="BARE CODE")
		self.code += '\t\t' + code + '\n'		
	def ForwardCalculation(self, code):
		self.Log(code, banner="FORWARD CALCULATION")
		if not code.startswith('//'):
			lhs = re.split(' =|\.|\-\>', code)[0]
			if not lhs in self.stateVariables + self.RValues.keys():
				code = 'Real ' + code
				self.intermediateVariables.append(lhs)
			self.code += '\t\t' + code + ';\n'
		else:
			self.code += '\t\t' + code + '\n'
	def Write(self, code):
		self.ForwardCalculation(code)
	#def Write(self, code):
	#	print "CODE:", code + '\n'
	#	self.code += '\t' + code + '\n'
	def LogIndent(self):
		self.logIndentationLevel += 1
	def LogDeindent(self):
		self.logIndentationLevel -= 1
	def Log(self, msg, banner="LOG"):
		print ''.join(['\t']*self.logIndentationLevel) + banner + ":", msg
	def GetCode(self):
		masterCode = '// AUTOGENERATED Wave digital filter ' + str(datetime.datetime.today()) + '\n'
		masterCode += '// Advanced Machine Audio Python WDF Generator ' + '\n'
		masterCode += '// Peter Raffensperger, 2012' + '\n'
		masterCode += 'class ' + self.circuitName + ' {\n'
		if self.headerCommentBlock != '':
			masterCode += '\t/*' + self.headerCommentBlock + '*/\n'
		masterCode += 'public:\n'
		
		#Constructor
		
		self.RParameters['sampleRate'] = 'Real'
		self.ConstructorParameters = self.RParameters.copy()
		self.ConstructorParameters.update(self.constructedItems)
		masterCode += '\t' + self.GetHeader(self.circuitName, self.ConstructorParameters, type='', isConstructor=True)
		if self.constructorList != '':
			masterCode += ' : ' + self.constructorList
		masterCode += '{\n'
		masterCode += '\t\tupdateRValues(' 
		RParametersSorted = self.RParameters.keys()[:]
		RParametersSorted.sort()
		masterCode += ', '.join(RParametersSorted) +');\n' 
		for sV in self.stateVariables:
			masterCode += '\t\t' + sV + ' = 0.0;\n'
		masterCode += '\t}\n\n'
		if self.destructor != '':
			masterCode += '\t~' + self.circuitName + '() {\n' + self.destructor + '\t}\n'
		
		#updateRValues
		
		masterCode += '\t' + self.GetHeader('updateRValues', self.RParameters) + self.RCode + '\t}\n'
		masterCode += '\n'
		masterCode += '\t' + self.GetHeader('advance', self.inputs, type='Real ') + self.code +  self.output + '\t}\n'
		masterCode += self.MakeGetStateFunction()
		masterCode += self.MakeSetStateFunction()
		masterCode += 'private:\n'
		masterCode += '\t//State variables\n'
		for sV in self.stateVariables:
			masterCode += '\tReal ' + sV + ';\n'
		masterCode += '\n\t//R values\n'
		for rV in self.RValues:
			masterCode += '\t' + self.RValues[rV] + ' ' + rV + ';\n'
		masterCode += '\t//Extra members\n'
		for mV in self.extraMembers:
			masterCode += '\t' + self.extraMembers[mV] + ' ' + mV + ';\n'
		
		masterCode += '};\n\n'
		
		
		
		for i in range(2):
			masterCode = self.EliminateUnusedVariables(masterCode)
		for i in range(5):
			masterCode = masterCode.replace(' )', ')')
			masterCode = masterCode.replace('- -', '+ ')
			masterCode = masterCode.replace('0.0 + ', '')
			masterCode = masterCode.replace('+ 0.0', '')
			masterCode = masterCode.replace('- 0.0', '')
			masterCode = masterCode.replace('0.0 - ', '-')
			#masterCode = masterCode.replace('  ', ' ')
			#masterCode = re.sub('.* .*?\*\(0.0\)', '0.0', masterCode)
		return masterCode
	def EliminateUnusedVariables(self, masterCode):
		cleanedCode = ''
		lines = masterCode.split('\n')
		for i in range(len(lines)):
			eliminateLine = False
			if lines[i].startswith('\t\t'):
				lhs = re.split(' =|\.|\-\>', lines[i].strip())[0]
				try:
					vn = lhs.split()[1] 
					if vn in self.intermediateVariables:
						if len(re.findall(vn, masterCode)) == 1:
							#import pdb; pdb.set_trace()
							eliminateLine = True
				except IndexError:
					pass
					
			if not eliminateLine:
				cleanedCode += lines[i] + '\n'
	
		return cleanedCode
	
	def GetHeader(self, functionName, args, type='void ', isConstructor=False):
		if args == []:
			args = '('
		elif args.__class__ == [].__class__:
			args = '(Real ' + ', Real '.join(args)
		else:
			keys = args.keys()
			keys.sort()
			args = '(' + ', '.join([args[key] + ' ' + key for key in keys])
		header = type + functionName + args + ')'
		if not isConstructor: 
			header += '{\n'
		return header
	def MakeGetStateFunction(self):
		getstatefn = '\n\t' + self.GetHeader('getState', [], type='vector<Real> ')
		getstatefn += '\t\t' + 'vector<Real> state('+ str(len(self.stateVariables)) + ', 0.0);\n'
		for i, sV in enumerate(self.stateVariables):
			getstatefn += '\t\t' + 'state[' + str(i) + '] = ' + sV + ';\n'
		getstatefn += '\t\treturn state;\n'
		getstatefn += '\t}\n'
		return getstatefn
	def MakeSetStateFunction(self):
		setstatefn = '\t' + 'void setState(vector<Real> state) {\n'
		setstatefn += '\t\tAssert(state.size() == ' + str(len(self.stateVariables)) + ');\n'
		for i, sV in enumerate(self.stateVariables):
			setstatefn += '\t\t' + sV + ' = state[' + str(i) + '];\n'
		setstatefn += '\t}\n'
		return setstatefn

class GeneratorWDFPort():
	def __init__(self, name, generator):
		self.name = name
		self.generator = generator
		self.b = ''
		self.a = ''
		self.R = ''
		self.mate = None
	def SetA(self, a):
		self.generator.Write("//" + self.name + "SetA")	

	def GetB(self):
		self.generator.Write("//" + self.name + "GetB")	
		self.generator.Log(self.name + '.GetB')
		return self.b
	def GetR(self):
		self.generator.Log(self.name + '.GetR')
		return self.name + 'R'
	def Connect(self, other):
		#assert(other.GetR() == self.R)
		self.mate = other
		other.mate = self
	def GetVoltage(self):
		"""
		a = v + Ri
		b = v - Ri
		v = a + b
		"""
		return '-(' + self.name + 'a + ' + self.b + ')'

class GeneratorWDFExternal(GeneratorWDFPort):
	def __init__(self, name, generator, setACommand, getBCommand):
		GeneratorWDFPort.__init__(self, name, generator)
		self.generator.RValue(self.name + 'R', self.name + 'R = R_' + self.name, 'R_' + self.name, intermediate=True)
		self.setACommand = setACommand
		self.getBCommand = getBCommand
	def GetB(self):
		self.generator.Write("//" + self.name + "GetB")
		self.b = self.getBCommand
		return self.b
	def SetA(self, a):
		self.generator.Write("//" + self.name + "SetA")
		self.generator.ForwardCalculation(self.name + "a = " + a)
		self.generator.ForwardCalculation(self.setACommand)
		

class GeneratorWDFResistor(GeneratorWDFPort):
	"""
	V = RI
	b = 0
	"""
	def __init__(self, name, generator):
		GeneratorWDFPort.__init__(self, name, generator)
		self.generator.RValue(self.name + 'R', self.name + 'R = R_' + self.name, 'R_' + self.name, intermediate=True)
		self.b = '0.0'
	def SetA(self, a):
		self.generator.Write("//" + self.name + "SetA")			
		pass

class GeneratorWDFCapacitor(GeneratorWDFPort):
	"""
	V = IR/phi
	b = a*z^-1
	
	R = 1/(2*C*fs)
	"""
	def __init__(self, name, generator):
		GeneratorWDFPort.__init__(self, name, generator)
		self.generator.RValue(self.name + 'R', self.name + 'R = 1.0 / (2.0*C_' + self.name + '*sampleRate)', 'C_' + self.name, intermediate=True)
		self.b = self.name + 'b'
		self.generator.StateVariable(self.name + 'a')
	def SetA(self, a):
		self.generator.Log(self.name + '.SetA')
		self.generator.Write(self.name + "a = " + a)
		
	def GetB(self):
		self.generator.Log(self.name + '.GetB')	
		self.generator.Write(self.b + ' = ' + self.name + 'a')
		return self.b
		
class GeneratorWDFInductor(GeneratorWDFPort):
	"""
	V = phi*IR
	b = -a*z^-1
	
	R = 2*L*fs
	"""
	def __init__(self, name, generator):
		GeneratorWDFPort.__init__(self, name, generator)
		self.generator.RValue(self.name + 'R', self.name + 'R = 2.0*L_' + self.name + '*sampleRate', 'L_' + self.name, intermediate=True)
		self.b = self.name + 'b'
		self.generator.StateVariable(self.name + 'a')		
	def SetA(self, a):
		self.generator.Log(self.name + '.SetA')
		self.generator.Write(self.name + "a = " + a)
		
	def GetB(self):
		self.generator.Log(self.name + '.GetB')	
		self.generator.Write(self.b + ' = -' + self.name + 'a')
		return self.b
		
class GeneratorWDFResistiveSource(GeneratorWDFPort): #Voltage source
	"""
	V = E + IR
	b = E
	
	"""
	def __init__(self, name, generator):
		GeneratorWDFPort.__init__(self, name, generator)
		self.generator.RValue(self.name + 'R', self.name + 'R = R_' + self.name, 'R_' + self.name, intermediate=True)
		self.generator.RValue(self.name + 'E', self.name + 'E = E_' + self.name, 'E_' + self.name)
		self.b = self.name + 'E'
	def SetA(self, a):
		pass

# class GeneratorWDFIdealVoltageSource(GeneratorWDFPort): #Voltage source
# 	"""
# 	b = 2e - a 
# 	"""
# 	def __init__(self, e, R): #Value of R doesn't matter
# 		GeneratorWDFPort.__init__(self, name, generator)
# 		self.e = e
# 	def SetE(self, e):
# 		self.e = e
# 	def GetB(self):
# 		a = self.mate.b #I hope the timing of this works right!
# 		return 2.0*self.e - a

# class GeneratorWDFResistiveCurrentSource(GeneratorWDFPort):
# 	"""
# 	source current = e / R
# 	b = a - 2e
# 	
# 	"""
# 	def __init__(self, sourceCurrent, R):
# 		GeneratorWDFPort.__init__(self, name, generator)
# 		self.b = E
# 	def SetSourceCurrent(self, E):
# 		self.b = E
		
class GeneratorWDFOpenCircuit(GeneratorWDFPort):
	"""
	b = a
	"""
	def __init__(self, R):
		GeneratorWDFPort.__init__(self, name, generator)
	def GetB(self):
		self.generator.Log(self.name + '.GetB')		
		return self.mate.GetB()

class GeneratorWDFShortCircuit(GeneratorWDFPort):
	"""
	b = -a
	"""
	def __init__(self, R):
		GeneratorWDFPort.__init__(self, name, generator)
	def GetB(self):
		self.generator.Log(self.name + '.GetB')		
		return -self.mate.GetB()
		
class GeneratorWDFTwoPort(GeneratorWDFPort):
	"""
	Signal flow is from the parent to the child
	"""
	def __init__(self, name, generator):
		GeneratorWDFPort.__init__(self, name, generator)
		self.childPort = GeneratorWDFPort(name + 'child', generator)
	def Connect(self, parent):
		GeneratorWDFPort.Connect(self, parent)
	def ConnectChild(self, child):
		self.childPort.Connect(child)
	def SetA(self, parentA):
		self.generator.Write("//" + self.name + "SetA")		
		self.a = parentA
		self.ComputeChildB() 
		self.childPort.mate.SetA(self.childPort.b)
	def GetB(self): #Gets parent side B
		self.generator.Write("//" + self.name + "GetB")	
		self.generator.Log(self.name + '.GetB')	
		self.childPort.a = self.childPort.mate.GetB()
		self.ComputeParentB()
		return self.b
	def ComputeChildB(self):
		self.childPort.b = self.a #Pass through
	def ComputeParentB(self):
		self.b = self.secondaryPort.a #Pass through
# 
# class GeneratorWDFBidirectionalUnitDelay(): #Use for breaking delay free loops and things
# 	def __init__(self, R):
# 		self.ports = [GeneratorWDFPort(R), GeneratorWDFPort(R)]
# 	def GetPort(self, portIndex):
# 		return self.ports[portIndex]
# 	def Advance(self):
# 		for p, q in zip([0, 1], [1, 0]):
# 			self.ports[p].b = self.ports[q].a
# 
class GeneratorWDFIdealTransformer(GeneratorWDFTwoPort):
	"""
	Primary = Parent
	Secondary = Child
	"""
	def __init__(self, name, generator):
		GeneratorWDFTwoPort.__init__(self, name, generator)
		self.generator.RValue(self.name + 'n', self.name + 'n = 1.0 / NpOverNs', 'NpOverNs')
		self.generator.RValue(self.name + 'OneOvern', self.name + 'OneOvern = NpOverNs')
	def ConnectChild(self, child):
		Rs = child.R
		self.R = Rs + '/(' + self.name + 'n*' + self.name + 'n)'
		self.generator.RValue(self.name + 'R', self.name + 'R = ' + self.R, intermediate=True)
		self.childPort.R = Rs
		GeneratorWDFTwoPort.ConnectChild(self, child)
		#self.childPort.Connect(child)
	def ComputeChildB(self):
		self.childPort.b = self.a + '*' + self.name + 'n'
	def ComputeParentB(self):
		self.b = self.childPort.a + '*' + self.name + 'OneOvern'

class GeneratorWDFInterconnect(GeneratorWDFPort):
	"""
	Port 3 is reflection free
	"""
	def __init__(self, name, generator):
		self.children = []
		self.childrensPorts = [GeneratorWDFPort(name + '_1', generator), GeneratorWDFPort(name + '_2', generator)]
		self.gamma1 = None
		GeneratorWDFPort.__init__(self, name + '_3', generator)
	def ConnectChild(self, child):
		childIndex = len(self.children)
		assert(childIndex <= 1)
		self.children.append(child)
		self.childrensPorts[childIndex].R = child.GetR()
		self.generator.RValue(self.childrensPorts[childIndex].name + 'R', self.childrensPorts[childIndex].name + 'R' + ' = ' + child.GetR(), intermediate=True)
		self.childrensPorts[childIndex].Connect(child)
	
	def SetA(self, parentsA):
		self.generator.Write("//" + self.name + "SetA")		
		self.generator.Log(self.name + '.SetA')
		self.generator.LogIndent()
		self.a = parentsA
		for childIndex in [0, 1]:
			self.generator.Log("  " + self.name + ".SetA " + str(childIndex))
			#self.ports[childIndex].b = self.ComputeB1Or2(childIndex) #The theoretically proper way
			#self.children[childIndex].SetA(self.ports[childIndex].GetB())
			self.children[childIndex].SetA(self.ComputeB1Or2(childIndex)) #Just cut to the chase
		self.generator.LogDeindent()
		
	def GetB(self):
		self.generator.Write("//" + self.name + "GetB")		
		self.generator.Log(self.name + '.GetB')		
		self.generator.LogIndent()
		for childIndex in [0, 1]:
			self.generator.Log("  " + self.name + ".GetB " + str(childIndex))
			self.childrensPorts[childIndex].SetA(self.children[childIndex].GetB())
		self.b = self.ComputeB3()
		self.generator.LogDeindent()
		return self.b
		
	def GetAs(self):
		a1 = self.childrensPorts[0].mate.b
		a2 = self.childrensPorts[1].mate.b
		a3 = self.a
		return a1, a2, a3
		
	def ComputeB3(self):
		return '0.0'
	def ComputeB1Or2(self, childIndex):
		return '0.0'

	
	
class GeneratorWDFParallelAdapter(GeneratorWDFInterconnect):
	"""
	Port 3 is reflection free
	"""
	def ConnectChild(self, child):
		GeneratorWDFInterconnect.ConnectChild(self, child)
		if len(self.children) == 2:
			G1 = '1.0 / ' + self.childrensPorts[0].GetR()
			G2 = '1.0 / ' + self.childrensPorts[1].GetR()
			G3 = G1 + ' + ' + G2
			self.R = '1.0 /(' + G3 + ')'
			self.generator.RValue(self.name + 'R', self.name + 'R' + ' = ' + self.R, intermediate=True)
			self.gamma1 = self.name + 'Gamma1'
			self.generator.Log(self.name + ' calculated gamma')				
			self.generator.RValue(self.gamma1, self.gamma1 + ' = ' + G1 + '/(' + G3 + ')')
			self.generator.RCheck('Assert(' + self.gamma1 + ' >= 0.0 && ' + self.gamma1 + ' <= 1.0)')

	def ComputeB1Or2(self, childIndex):
		a1, a2, a3 = self.GetAs()
		if childIndex == 0:
			b1 = a3 + ' + ' + a2 + ' - ' + a1 + ' - ' + self.gamma1 + '*(' + a2 + ' - ' + a1 + ')'
			self.generator.ForwardCalculation(self.name + 'b1 = ' + b1)
			return self.name + 'b1'
		else:
			b2 = a3 + ' - ' + self.gamma1 + '*(' + a2 + ' - ' + a1 + ')'
			self.generator.ForwardCalculation(self.name + 'b2 = ' + b2)
			return self.name + 'b2'

	def ComputeB3(self):
		a1, a2, a3 = self.GetAs()
		b3 = a2 + ' - ' + self.gamma1 + '*(' + a2 + ' - ' + a1 + ')'
		self.generator.ForwardCalculation(self.name + 'b3 = ' + b3)
		return self.name + 'b3'
class GeneratorWDFSeriesAdapter(GeneratorWDFInterconnect):
	"""
	Port 3 is reflection free
	"""
	def ConnectChild(self, child):
		GeneratorWDFInterconnect.ConnectChild(self, child)
		if len(self.children) == 2:
			R1 = self.childrensPorts[0].mate.GetR() 
			R2 = self.childrensPorts[1].mate.GetR()
			R3 = '(' + R1 + ' + ' + R2 + ')'
			self.R = R3
			self.generator.RValue(self.name + 'R', self.name + 'R' + ' = ' + self.R, intermediate=True)
			self.gamma1 = self.name + 'Gamma1'
			self.generator.Log(self.name + ' calculated gamma')							
			self.generator.RValue(self.gamma1, self.gamma1 + ' = ' + R1 + '/' + R3)
			self.generator.RCheck('Assert(' + self.gamma1 + ' >= 0.0 && ' + self.gamma1 + ' <= 1.0)')			
			#print self.gamma1

	def ComputeB1Or2(self, childIndex):
		a1, a2, a3 = self.GetAs()
		if childIndex == 0:
			b1 = a1 + ' - ' + self.gamma1 + '*(' + a1 + ' + ' + a2 + ' + ' + a3 + ')'
			self.generator.ForwardCalculation(self.name + 'b1 = ' + b1)
			return self.name + 'b1'
		else:
			b2 = '-(' + a1  + ' + ' + a3  + ' - ' + self.gamma1 + '*(' + a1 + ' + ' + a2 + ' + ' + a3 + '))'
			self.generator.ForwardCalculation(self.name + 'b2 = ' + b2)
			return self.name + 'b2'
		
	def ComputeB3(self):
		a1, a2, a3 = self.GetAs()		
		b3 = '-(' + a1 + ' + ' + a2 + ')'
		self.generator.ForwardCalculation(self.name + 'b3 = ' + b3)
		return self.name + 'b3'
		
def RCHandDSP(numTimeSteps):
	sampleRate = 1000.0
	R = 1000.0
	C = 10e-6
	R2 = 1.0 / (2.0*C*sampleRate)
	R1 = R - R2
	R3 = R1 + R2
	
	e = 1.0
	
	y1 = R1 / R3
	#print y1
	b1 = 0.0
	b1Last = 0.0
	for t in range(numTimeSteps):
		b1 = (2.0*e*(1.0 - y1) + y1*b1Last) / (2.0 - y1)
		output = -2.0*e + b1 + b1Last
		a1 = 2*e - b1
		a2 = -1.0*b1Last
		b1s = a1 + -y1*(a1 + a2)
		vc = -1.0*b1-b1Last
		#print a1, a2, b1s, b1, output, vc, vc + output
		b1Last = b1

def RCGeneratorWDF():
	g = Generator('RCSeries')
	#V = GeneratorWDFResistiveSource(10, 100)
	R = GeneratorWDFResistor('R1', g)
	C = GeneratorWDFCapacitor('C1', g)
	Conn = GeneratorWDFSeriesAdapter('SeriesConn1', g)
	Conn.ConnectChild(R)
	Conn.ConnectChild(C)
	
	e = 'vin'
	g.Input('vin')
	a = Conn.GetB()
	b = '(2.0*' + e + ' - ' + a + ')'
	g.ForwardCalculation('b = ' + b)
	Conn.SetA('b')
	g.Output('2.0*vin - ' + C.GetVoltage())
	#print a, b, R.GetVoltage()
	print g.GetCode()


	#print a, b, R.GetVoltage()


def RCGeneratorWDFParallel():
	sampleRate = 10000.0
	g = Generator('RCParallel')
	#V = GeneratorWDFResistiveSource(10, 100)
	R = GeneratorWDFResistor('R1', g)
	C = GeneratorWDFCapacitor('C1', g)
	Conn = GeneratorWDFParallelAdapter('ParallelConn1', g)
	Conn.ConnectChild(R)
	Conn.ConnectChild(C)
	
	e = 'vin'
	g.Input('vin')
	a = Conn.GetB()
	b = e
	Conn.SetA(b)
	g.Output(C.GetVoltage())
	#print a, b, R.GetVoltage()
	print g.GetCode()

def WDFCircuit(sampleRate, R_R1, C_C1, C1a):
	R1R = R_R1
	C1R = 1.0 / (2.0*C_C1*sampleRate)
	ParallelConn1_3Gamma1 = 1.0 / R1R/(1.0 / R1R + 1.0 / C1R)
	ParallelConn1_1a = 0.0
	C1b = C1a
	ParallelConn1_2a = C1b
	C1a = ein - ParallelConn1_3Gamma1*(C1b - 0.0)
	return C1a

		
if __name__ == '__main__':
	#sampleRate, R_R1, C_C1, C1a = 1000.0, 100
	#for t in range(10):
	#	Ca1 = WDFCircuit(sampleRate, R_R1, C_C1, C1a)
	RCGeneratorWDF()

# 	import time
# 	numTimeSteps = 50000
# 	for fn, msg in (RCHandDSP, "Hand"), (RCGeneratorWDF, "WDF"):
# 		print msg
# 		start = time.time()
# 		fn(numTimeSteps)
# 		end = time.time()
# 		print "Time take =", end - start

	#RCWDFParallel()
	#import sys
	#raise sys.exit(0)