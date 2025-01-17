
# Add the parent folder (outside of `examples`) to the path, so we can find the `arch` module
import sys, os
sys.path.append(os.path.dirname(sys.path[0]))

try:
    import colored_traceback.auto
except ImportError:
    pass
    
import abc
import arch.port as port
from arch.port import var
from arch.block import Block
from arch.connectivity import Connectivity
from arch.models import Model, SymbolicModel, NumericModel, SourceModel
from arch.blocks.optics import Beamsplitter, PhaseShifter, MachZehnder
from arch.blocks.sources import LaserCW
from arch.architecture import Architecture


if __name__ == '__main__':
	
	"""
	print ("Testing NumericModel composition")
	
	port_a  = var("a",  kind=port.kind.real, direction=port.direction.inp, default=0)
	port_bo = var("bo", kind=port.kind.real, direction=port.direction.out, default=0)
	port_bi = var("bi", kind=port.kind.real, direction=port.direction.inp, default=0)
	port_c  = var("c",  kind=port.kind.real, direction=port.direction.inp, default=0)
	port_d  = var("d",  kind=port.kind.real, direction=port.direction.out, default=0)
	
	# Funcs need to take a dict as input, keyed by port
	#  return a dict as output, keyed by port
	
	ports_bo = {port_a}
	def func_bo(port_dict):
		a = port_dict[port_a]
		return {port_bo: 2*a}
		
	mod_b = NumericModel("mod_b", ports={port_a, port_bo}, out_func=func_bo)
	
	ports_d = {port_bi, port_c}
	def func_d(port_dict):
		b = port_dict[port_bi]
		c = port_dict[port_c]
		return {port_d: b + c}
	
	mod_d = NumericModel("mod_d", ports={port_bi, port_c, port_d}, out_func=func_d)
	
	con = Connectivity( [(port_bo, port_bi)] )
	
	mod_comp = NumericModel.compound(name="comp", models={mod_b, mod_d}, connectivity=con)
	
	state = {port_a:1, port_c:0}
	print(mod_comp.out_func(state))
	print(state)
	"""
	
	
	print ("Welcome to the new arch")
	
	laser = LaserCW()
	mz0 = MachZehnder()
	mz1 = MachZehnder()#mz0.copy()
	ps0 = PhaseShifter()
	ps1 = PhaseShifter()
	bs = Beamsplitter()
	bs1 = Beamsplitter()
	
	laser.delay = 1
	mz0.delay = 1
	mz1.delay = 1
	ps0.delay = 1
	ps1.delay = 1
	bs.delay = 1
	
	
	config = 'complex'
	
	if config == 'simple':
		connections = Connectivity( [
						(ps0.out, ps1.inp)
						] )
	
	
	elif config == 'complex':
	
		connections = Connectivity( [
						(laser.out, mz0.in0),
						(mz0.out0, ps0.inp),
						(mz0.out1, ps1.inp),
						(ps0.out, bs.in0),
						(ps1.out, bs.in1),
						(bs.out0, mz1.in0),
						(bs.out1, mz1.in1),
						] )
		
	elif config == 'loops':
		
	
		connections = Connectivity( [
						(bs.out1, ps0.inp),
						(ps0.out, bs.in1),
						] )
		
	elif config == 'unbalanced delay':
		
	
		connections = Connectivity( [
						(bs.out0, ps0.inp),
						(ps0.out, bs1.in0),
						(bs.out1, bs1.in1),
						] )
		
	else:
		raise RuntimeError("Bad config")
		
	
	cm = bs.model.compound("compound name", connections.models, connections)
	
	
	print('\ncm is',cm)
	
	print('cm is',cm)
	print('\n out exprs',cm.out_exprs)
	print('out func', cm.out_func)
	print('ports',cm.ports)
	print('in ports',cm.in_ports)
	print('out ports',cm.out_ports)
	print('properties',cm.properties)
	if 'optical' in cm.properties:
		print('U',cm.U)
	if 'symbolic' in cm.properties:
		print('out exprs',cm.out_exprs)
		
	import time
	
	
	state = cm.default_input_state
	state[ps0.phi] = 3.14
	state[bs.R] = 0.01
	state[bs.in0] = 1.0
	print("default input state",state)
	
	eval_time = time.time()
	state = cm.out_func(state)
	eval_time = time.time() - eval_time
	
	print("default output state",state)
		
	print(f"Took {eval_time} s")
	
# 	oe = cm.out_exprs[mz1.out0]
# 	import IPython
# 	IPython.embed()
# 	quit()
	
		
	import networkx as nx
	
	
	def get_delay_map(connectivity, default_delay=0, block_delay_func=lambda b:b.delay):
		"""
		Build map between the external output ports of `connectivity` and its input ports
		mapping the delay along each path between those ports. Checks that all paths have
		matching delays.
		
		connectivity: `Connectivity` object describing configuration
		default_delay: value to be taken as default when no delay is present
		block_delay_func: function to compute delay from block value; exceptions use default
		"""
		
		def _integrate_path_delay(path):
			"""Add up delay attributes of blocks in list `path`"""
			
			total_delay = 0
			for block in path:
				try:
					delay = block_delay_func(block)
				except:
					delay = default_delay
				total_delay += delay
			
			return total_delay
		
		delay_map = dict()
		for op in connectivity.external_out_ports:
			delay_map |= {op:dict()}
			for ip in connectivity.external_in_ports:
				
				if ip.block is op.block:
					# If input port and output port are from the same block, no delay
					paths = [[ip.block]]
				else:
					# Find all paths between input and output blocks, integrate delays
					paths = list(nx.algorithms.simple_paths.all_simple_paths(
										connectivity.block_graph, ip.block, op.block))
				
				delays = {_integrate_path_delay(p) for p in paths}
				
				# Do checks
				if not len(delays):
					# No path exists
					delays = [default_delay]
				
				assert len(delays) == 1, f"Varying delays found between {ip} and {op}"
				
				# Update map
				delay_map[op] |= {ip:next(iter(delays))}
				
		return delay_map
	
	
	
	"""
	NOTE TO SELF:
	
	Need a simulator that simulates each internal variable at each time step.
	Simulator might gobble up subgraphs with synchronised time:
		1. examine when delay paths diverge
		2. chop back subgraph until that point
		3. compound
		4. repeat
	Compile all outputs as a function of all inputs
	Each frame:
		1. Compute all internal and external port values
		2. Handle delays
	"""
	
	
	connections.draw(draw_ports=True)
	
	dm = get_delay_map(connections)
	print(dm)
	print(cm)
	
	print(cm.in_ports)
	print(cm.out_ports)
	
	
# 	connections.draw()
	
	# Functions for producing time series
	def constant(v):
		return lambda t : v
		
	def step(v0, v1, t_step):
		return lambda t : v0 if t < t_step else v1
		
	def sinusoid(amp, offset, t_period, phase):
		from math import sin, pi
		return lambda t : (amp/2)*sin(2*pi*t/t_period + phase) + offset
		
	def ramp(v0, v1, t_period, phase):
		from math import pi
		return lambda t : (v1-v0)*(t%t_period)/t_period + v0
	
	
	
	
	
	from math import pi
	
	in_time_funcs = {
				laser.P: step(0,1.1,50), 
				mz0.phi: constant(pi/2), 
				mz1.phi: constant(pi/2),
				ps0.phi: ramp(0, pi, 50, 0),
				ps1.phi: constant(0)}
	
	
	
	states_ts = []
	
	state = cm.default_input_state
	
	import time
	
	t_setup = 0
	t_out_func = 0
	n_out_func_calls = 0
	t_close_copy = 0
	
	t_start = time.time()
	for t in range(200):
		
		for op in cm.out_ports:
			
			# Get delayed inputs
			t0 = time.time()
			for ip in cm.in_ports:
				if ip in in_time_funcs:
					state |= {ip:in_time_funcs[ip](t - dm[op][ip])}
			t_setup += time.time()-t0
				
			# Update output using delayed inputs
			t0 = time.time()
			state |= cm.out_func(state)
			t_out_func += time.time()-t0
			n_out_func_calls += 1
			
			# Update inputs to current time
			t0 = time.time()
			for ip in cm.in_ports:
				if ip in in_time_funcs:
					state |= {ip:in_time_funcs[ip](t)}
			
			states_ts.append((t,state.copy()))
			t_close_copy += time.time()-t0
	
	t_total = time.time() - t_start
	
		
	
	print("Spent time:")
	print(" t_setup =",t_setup)
	print(" t_out_func =",t_out_func,f" in {n_out_func_calls} calls")
	print(" t_close_copy =",t_close_copy)
	print(" t_total =",t_total)
	
	from matplotlib import pyplot
	
	pyplot.plot([s[0] for s in states_ts], [s[1][laser.P] for s in states_ts])
	pyplot.plot([s[0] for s in states_ts], [s[1][ps0.phi] for s in states_ts])
	pyplot.plot([s[0] for s in states_ts], [abs(s[1][mz1.out0]) for s in states_ts])
	pyplot.plot([s[0] for s in states_ts], [abs(s[1][mz1.out1]) for s in states_ts])
	pyplot.show()
	
	quit()
	
	
# 	from arch.block import AutoCompoundBlock
# 	acb = AutoCompoundBlock(blocks=[laser,mz0], connectivity=connections)
# 	print("ACB outs:",acb.model.out_exprs)
	
# 	acb = AutoCompoundBlock(blocks=[laser,mz0,ps0,ps1,mz1,bs], connectivity=connections)
# 	print("Can use favourite port labels:", mz0.in1 is acb.MZ0_in1)
	
# 	from math import pi
# 	out_dict = acb.model.out_func(in_port_values={mz0.in0:1, mz0.in1:0, mz1.phi:pi/2})
	
# 	acb.connectivity.draw(draw_ports=True)
# 	acb.connectivity.draw(draw_ports=False)
	
	
	
# 	arch = Architecture(connections, None)
	
# 	print([(sym,sym.data) for m in ps.models for sym in m.out_exprs[0].free_symbols])