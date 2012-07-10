/************************************************************************************
* 
* Wavechild670 v0.1 
* 
* wavechild670.h
* 
* By Peter Raffensperger 10 July 2012
* 
* Reference:
* Toward a Wave Digital Filter Model of the Fairchild 670 Limiter, Raffensperger, P. A., (2012). 
* Proc. of the 15th International Conference on Digital Audio Effects (DAFx-12), 
* York, UK, September 17-21, 2012.
* 
* Note:
* Fairchild (R) a registered trademark of Avid Technology, Inc., which is in no way associated or 
* affiliated with the author.
* 
* License:
* Wavechild670 is licensed under the GNU GPL v2 license. If you use this
* software in an academic context, we would appreciate it if you referenced the original
* paper.
* 
************************************************************************************/



#ifndef WAVECHILD670_H
#define WAVECHILD670_H

#include "Misc.h"

#include <fftw3.h>

#include "sidechainamplifier.h"
#include "variablemuamplifier.h"
#include "basicdsp.h"
#include "scope.h"

#define LEVELTC_CIRCUIT_DEFAULT_C_C1 2e-6
#define LEVELTC_CIRCUIT_DEFAULT_C_C2 8e-6
#define LEVELTC_CIRCUIT_DEFAULT_C_C3 20e-6
#define LEVELTC_CIRCUIT_DEFAULT_R_R1 220e3
#define LEVELTC_CIRCUIT_DEFAULT_R_R2 1e9
#define LEVELTC_CIRCUIT_DEFAULT_R_R3 1e9

class Wavechild670Parameters {
public:
	Wavechild670Parameters(Real inputLevelA_, Real ACThresholdA_, uint timeConstantSelectA_, Real DCThresholdA_, 
	Real inputLevelB_, Real ACThresholdB_, uint timeConstantSelectB_, Real DCThresholdB_, 
	bool sidechainLink_, bool isMidSide_, bool useFeedbackTopology_, Real outputGain_, bool hardClipOutput_){
		inputLevelA = inputLevelA_;
		ACThresholdA = ACThresholdA_; 
		timeConstantSelectA = timeConstantSelectA_; 
		DCThresholdA = DCThresholdA_; 
				
		inputLevelB = inputLevelB_; 
		ACThresholdB = ACThresholdB_; 
		timeConstantSelectB = timeConstantSelectB_; 
		DCThresholdB = DCThresholdB_; 
				
		sidechainLink = sidechainLink_; 
		isMidSide = isMidSide_; 
		useFeedbackTopology = useFeedbackTopology_;
		outputGain = outputGain_;
		hardClipOutput = hardClipOutput_;
		
	}
	virtual ~Wavechild670Parameters() {}
public:
	Real inputLevelA;
	Real ACThresholdA; 
	uint timeConstantSelectA; 
	Real DCThresholdA; 
	
	Real inputLevelB; 
	Real ACThresholdB; 
	uint timeConstantSelectB; 
	Real DCThresholdB; 
	
	bool sidechainLink; 
	bool isMidSide; 
	bool useFeedbackTopology;
	
	Real outputGain;
	bool hardClipOutput;
private:
	Wavechild670Parameters() {}
};

class Wavechild670 {
public:
	Wavechild670(Real sampleRate_, Wavechild670Parameters& parameters) : 
	sampleRate(sampleRate_),
	useFeedbackTopology(parameters.useFeedbackTopology), isMidSide(parameters.isMidSide), sidechainLink(parameters.sidechainLink),
	sidechainAmplifierA(sampleRate, parameters.ACThresholdA, parameters.DCThresholdA), sidechainAmplifierB(sampleRate, parameters.ACThresholdB, parameters.DCThresholdB), 
	levelTimeConstantCircuitA(LEVELTC_CIRCUIT_DEFAULT_C_C1, LEVELTC_CIRCUIT_DEFAULT_C_C2, LEVELTC_CIRCUIT_DEFAULT_C_C3, LEVELTC_CIRCUIT_DEFAULT_R_R1, LEVELTC_CIRCUIT_DEFAULT_R_R2, LEVELTC_CIRCUIT_DEFAULT_R_R3, sampleRate), 
	levelTimeConstantCircuitB(LEVELTC_CIRCUIT_DEFAULT_C_C1, LEVELTC_CIRCUIT_DEFAULT_C_C2, LEVELTC_CIRCUIT_DEFAULT_C_C3, LEVELTC_CIRCUIT_DEFAULT_R_R1, LEVELTC_CIRCUIT_DEFAULT_R_R2, LEVELTC_CIRCUIT_DEFAULT_R_R3, sampleRate), 
	VlevelCapA(0.0), VlevelCapB(0.0),
	signalAmplifierA(sampleRate), signalAmplifierB(sampleRate), inputLevelA(parameters.inputLevelA), inputLevelB(parameters.inputLevelB) {
		setParameters(parameters);
		SCOPE_PROBE("Vgate", 2);
		SCOPE_PROBE("Vcathode", 4);
		SCOPE_PROBE("Vak", 4);
		SCOPE_PROBE("VakModel", 4);
		SCOPE_PROBE("VplateE", 4);
		SCOPE_PROBE("Va", 4);
		SCOPE_PROBE("Vsc", 2);			
		SCOPE_PROBE("VgPlus", 2);
		SCOPE_PROBE("Vamp", 2);
	}
	virtual ~Wavechild670() {}

	virtual void setParameters(Wavechild670Parameters& parameters){
		inputLevelA = parameters.inputLevelA;
		sidechainAmplifierA.setThresholds(parameters.ACThresholdA, parameters.DCThresholdA); 
				
		inputLevelB = parameters.inputLevelB; 
		sidechainAmplifierB.setThresholds(parameters.ACThresholdB, parameters.DCThresholdB); 
		
		select670TimeConstants(parameters.timeConstantSelectA, parameters.timeConstantSelectB);
		
		sidechainLink = parameters.sidechainLink; 
		isMidSide = parameters.isMidSide; 
		useFeedbackTopology = parameters.useFeedbackTopology;		
		outputGain = parameters.outputGain;
		hardClipOutput = parameters.hardClipOutput;
		
		LOG_INFO("Internals");
		LOG_INFO("inputLevelA=" << inputLevelA); 
		LOG_INFO("inputLevelB=" << inputLevelB); 
		LOG_INFO("sidechainLink=" << sidechainLink); 
		LOG_INFO("isMidSide=" << isMidSide); 
		LOG_INFO("useFeedbackTopology=" << useFeedbackTopology); 
		
		LOG_INFO("sampleRateOverride=" << sampleRate);
		LOG_INFO("outputGain=" << outputGain);
	}
	
	virtual void warmUp(Real warmUpTimeInSeconds=0.5){
		ulong numSamples = (ulong) warmUpTimeInSeconds*sampleRate;
		for (ulong i = 0; i < numSamples/2; i += 1) {
			Real VoutA = signalAmplifierA.advanceAndGetOutputVoltage(0.0, VlevelCapA);
			Real VoutB = signalAmplifierB.advanceAndGetOutputVoltage(0.0, VlevelCapB);
		}
		for (ulong i = 0; i < numSamples/2; i += 1) {
			Real VoutA = signalAmplifierA.advanceAndGetOutputVoltage(0.0, VlevelCapA);
			Real VoutB = signalAmplifierB.advanceAndGetOutputVoltage(0.0, VlevelCapB);
			advanceSidechain(VoutA, VoutB); //Feedback topology with implicit unit delay between the sidechain input and the output, 
		}
		SCOPE_RESET();
	}

	//virtual void process(Real *VinputLeft, Real *VinputRight, Real *VoutLeft, Real *VoutRight, ulong numSamples) {
	virtual void process(Real *VinputInterleaved, Real *VoutInterleaved, ulong numSamples) {
		Assert(VinputInterleaved);
		Assert(VoutInterleaved);
		static uint numChannels = 2;
		
		for (ulong i = 0; i < numSamples; i += numChannels) {
			uint j = i + 1;
			Real VinputA;
			Real VinputB;
			Assert(!isnan(*(VinputInterleaved+i)));
			Assert(!isnan(*(VinputInterleaved+j)));
			if (isMidSide) {
				VinputA = (*(VinputInterleaved+i) + *(VinputInterleaved+i))/sqrt(2.0);
				VinputB = (*(VinputInterleaved+j) - *(VinputInterleaved+j))/sqrt(2.0);
			}
			else {
				VinputA = *(VinputInterleaved+i);
				VinputB = *(VinputInterleaved+j);
			}
			SCOPE("VinputA", VinputA);
			SCOPE("VinputB", VinputB);
			VinputA *= inputLevelA;
			VinputB *= inputLevelB;
			
			
			if (!useFeedbackTopology) { // => Feedforward
				advanceSidechain(VinputA, VinputB); //Feedforward topology
			}
			Real VoutA = signalAmplifierA.advanceAndGetOutputVoltage(VinputA, VlevelCapA);
			Real VoutB = signalAmplifierB.advanceAndGetOutputVoltage(VinputB, VlevelCapB);
			if (useFeedbackTopology) {
				advanceSidechain(VoutA, VoutB); //Feedback topology with implicit unit delay between the sidechain input and the output, 
				//and probably an implicit unit delay between the sidechain capacitor voltage input and the capacitor voltage 
				//(at least they're not the proper WDF coupling between the two)
			}
			
			
			Real VoutLeft;
			Real VoutRight;			
			
			if (isMidSide) {
				VoutLeft = (VoutA + VoutB)/sqrt(2.0);
				VoutRight  = (VoutA - VoutB)/sqrt(2.0);
			}
			else {
				VoutLeft = VoutA;
				VoutRight = VoutB;
			}
			if (hardClipOutput){
				VoutLeft = BasicDSP::clipWithWarning(VoutLeft * outputGain, -1.0, 1.0);
				VoutRight = BasicDSP::clipWithWarning(VoutRight * outputGain, -1.0, 1.0);
			}
			else {
				VoutLeft = VoutLeft * outputGain;
				VoutRight = VoutRight * outputGain;
			}
			
			SCOPE("VoutLeft", VoutLeft);
			SCOPE("VoutRight", VoutRight);			
			
			*(VoutInterleaved + i) = VoutLeft;
			*(VoutInterleaved + j) = VoutRight;
		}
	}

protected:
	virtual void select670TimeConstants(uint tcA, uint tcB){
		Assert(tcA >= 1);
		Assert(tcA <= 6);
		tcA -= 1;
		levelTimeConstantCircuitA.updateRValues(levelTimeConstantCircuitComponentValues[tcA][0], levelTimeConstantCircuitComponentValues[tcA][1], levelTimeConstantCircuitComponentValues[tcA][2], levelTimeConstantCircuitComponentValues[tcA][3], levelTimeConstantCircuitComponentValues[tcA][4], levelTimeConstantCircuitComponentValues[tcA][5], sampleRate);
		Assert(tcB >= 1);
		Assert(tcB <= 6);
		tcB -= 1;
		levelTimeConstantCircuitA.updateRValues(levelTimeConstantCircuitComponentValues[tcB][0], levelTimeConstantCircuitComponentValues[tcB][1], levelTimeConstantCircuitComponentValues[tcB][2], levelTimeConstantCircuitComponentValues[tcB][3], levelTimeConstantCircuitComponentValues[tcB][4], levelTimeConstantCircuitComponentValues[tcB][5], sampleRate);
	}

	virtual void advanceSidechain(Real VinSidechainA, Real VinSidechainB) {
	
		Real sidechainCurrentA = sidechainAmplifierA.advanceAndGetCurrent(VinSidechainA, VlevelCapA);
		Real sidechainCurrentB = sidechainAmplifierB.advanceAndGetCurrent(VinSidechainB, VlevelCapB);
		SCOPE("sidechainCurrentA", sidechainCurrentA);
		SCOPE("sidechainCurrentB", sidechainCurrentA);
		//LOG_SAMPLE1(VinSidechainA << "V " << VinSidechainB << "V ");
		//LOG_SAMPLE1(sidechainCurrentA << "A " << sidechainCurrentB << "A ");
		if (sidechainLink) {
			Real sidechainCurrentTotal = (sidechainCurrentA + sidechainCurrentB)/2.0;// #Effectively compute the two circuits in parallel, crude but effective (I haven't prove this is exactly right)
			SCOPE("sidechainCurrentTotal", sidechainCurrentTotal);
			Real VlevelCapAx = levelTimeConstantCircuitA.advance(sidechainCurrentTotal);
			Real VlevelCapBx = levelTimeConstantCircuitB.advance(sidechainCurrentTotal); // #maintain the voltage in circuit B in case the user disengages the link
			VlevelCapA = (VlevelCapAx + VlevelCapBx) / 2.0;
			VlevelCapB = (VlevelCapAx + VlevelCapBx) / 2.0;
		}
		else {
			VlevelCapA = levelTimeConstantCircuitA.advance(sidechainCurrentA);
			VlevelCapB = levelTimeConstantCircuitB.advance(sidechainCurrentB);
		}
		SCOPE("VlevelCapA", VlevelCapA);
		SCOPE("VlevelCapB", VlevelCapB);
	}	

protected:
	Real sampleRate;
	Real outputGain;
	bool hardClipOutput;
	
	Real VlevelCapA;
	Real VlevelCapB;

	Real inputLevelA;
	Real inputLevelB;

	bool useFeedbackTopology;
	bool isMidSide;
	bool sidechainLink;
	SidechainAmplifier sidechainAmplifierA;
	SidechainAmplifier sidechainAmplifierB;
	LevelTimeConstantCircuit levelTimeConstantCircuitA;
	LevelTimeConstantCircuit levelTimeConstantCircuitB;
	VariableMuAmplifier signalAmplifierA;
	VariableMuAmplifier signalAmplifierB;
	
	static const Real Wavechild670::levelTimeConstantCircuitComponentValues[6][6];
};


#endif