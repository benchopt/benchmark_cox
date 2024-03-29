import warnings
from benchopt import BaseSolver, safe_import_context

with safe_import_context() as import_ctx:
    from skglm.datafits import Cox
    from skglm.penalties import L1_plus_L2, L2
    from skglm.solvers import ProxNewton, LBFGS
    from skglm.utils.jit_compilation import compiled_clone


class Solver(BaseSolver):

    name = 'skglm'

    parameters = {
        "solver": ["Prox-Newton", "L-BFGS"]
    }

    requirements = [
        "pip:git+https://github.com/scikit-learn-contrib/skglm.git@main",
    ]

    stopping_strategy = 'iteration'

    def __init__(self, solver="Prox-Newton"):
        self.solver_name = solver

    def set_objective(self, X, y, alpha, l1_ratio, use_efron):
        self.X, self.y = X, y
        self.l1_ratio = l1_ratio

        warnings.filterwarnings('ignore')
        if self.solver_name == "Prox-Newton":
            # fit ProxNewton
            self.datafit = compiled_clone(Cox(use_efron))
            self.penalty = compiled_clone(L1_plus_L2(alpha, l1_ratio))

            self.datafit.initialize(X, y)
            self.solver = ProxNewton(fit_intercept=False, tol=1e-9)
        elif self.solver_name == "L-BFGS":
            # L-BFGS
            self.datafit = compiled_clone(Cox(use_efron))
            self.penalty = compiled_clone(L2(alpha))

            self.datafit.initialize(X, y)

            self.solver = LBFGS(tol=1e-9)
        else:
            raise ValueError(
                f"Solver Parameter `{self.solver_name}` is not "
                f"supported in {self.name}"
            )

    def run(self, n_iter):
        self.solver.max_iter = n_iter

        w, *_ = self.solver.solve(
            self.X, self.y, self.datafit, self.penalty
        )
        self.w = w

    def get_result(self):
        return dict(w=self.w)

    def skip(self, X, y, alpha, l1_ratio, use_efron):
        if alpha == 0. and self.solver == "Prox-Newton":
            reason = (f"{self.name}:{self.solver} does not handle"
                      " unpenalized Cox estimation.")
            return True, reason

        if l1_ratio != 0. and self.solver == "L-BFGS":
            reason = (f"{self.name}:{self.solver} handles only "
                      "L2 Cox regularization")
            return True, reason

        return False, None

    def warm_up(self):
        # cache numba compilation
        self.run(4)
