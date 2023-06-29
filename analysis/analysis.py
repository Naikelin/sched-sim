from evalys.jobset import JobSet
import matplotlib.pyplot as plt

js = JobSet.from_csv("../output/sim_sched_jobs.csv")
js.plot(with_details=True)

plt.savefig('grafica.png')