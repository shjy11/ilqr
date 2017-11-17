# -*- coding: utf-8 -*-
"""Dynamics model."""

import six
import abc
import theano
import numpy as np
import theano.tensor as T
from .autodiff import as_function, hessian_vector, jacobian_vector


@six.add_metaclass(abc.ABCMeta)
class Dynamics():

    """Dynamics Model."""

    @property
    @abc.abstractmethod
    def state_size(self):
        """State size."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def action_size(self):
        """Action size."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def has_hessians(self):
        """Whether the second order derivatives are available."""
        raise NotImplementedError

    @abc.abstractmethod
    def f(self, x, u):
        """Dynamics model.

        Args:
            x: Current state [state_size].
            u: Current control [control_size].

        Returns:
            Next state [state_size].
        """
        raise NotImplementedError

    @abc.abstractmethod
    def f_x(self, x, u):
        """Partial derivative of dynamics model with respect to x.

        Args:
            x: Current state [state_size].
            u: Current control [control_size].

        Returns:
            df/dx [state_size, state_size].
        """
        raise NotImplementedError

    @abc.abstractmethod
    def f_u(self, x, u):
        """Partial derivative of dynamics model with respect to u.

        Args:
            x: Current state [state_size].
            u: Current control [control_size].

        Returns:
            df/du [state_size, action_size].
        """
        raise NotImplementedError

    @abc.abstractmethod
    def f_xx(self, x, u):
        """Second partial derivative of dynamics model with respect to x.

        Note:
            This is not necessary to implement if you're planning on skipping
            Hessian evaluation as the iLQR implementation does by default.

        Args:
            x: Current state [state_size].
            u: Current control [control_size].

        Returns:
            d^2f/dx^2 [state_size, state_size, state_size].
        """
        raise NotImplementedError

    @abc.abstractmethod
    def f_ux(self, x, u):
        """Second partial derivative of dynamics model with respect to u and x.

        Note:
            This is not necessary to implement if you're planning on skipping
            Hessian evaluation as the iLQR implementation does by default.

        Args:
            x: Current state [state_size].
            u: Current control [control_size].

        Returns:
            d^2f/dudx [state_size, action_size, state_size].
        """
        raise NotImplementedError

    @abc.abstractmethod
    def f_uu(self, x, u):
        """Second partial derivative of dynamics model with respect to u.

        Note:
            This is not necessary to implement if you're planning on skipping
            Hessian evaluation as the iLQR implementation does by default.

        Args:
            x: Current state [state_size].
            u: Current control [control_size].

        Returns:
            d^2f/du^2 [state_size, action_size, action_size].
        """
        raise NotImplementedError


class AutoDiffDynamics(Dynamics):

    """Auto-differentiated Dynamics Model."""

    def __init__(self, f, x_inputs, u_inputs, hessians=False):
        """Constructs an AutoDiffDynamics model.

        Args:
            f: Vector Theano tensor expression.
            x_inputs: Theano state input variables.
            u_inputs: Theano action input variables.
            hessians: Evaluate the dynamic model's second order derivatives.
                Default: only use first order derivatives. (i.e. iLQR instead
                of DDP).
        """
        self._inputs = np.hstack([x_inputs, u_inputs]).tolist()

        self._x_inputs = x_inputs
        self._u_inputs = u_inputs

        x_dim = len(x_inputs)
        u_dim = len(u_inputs)
        self._state_size = x_dim
        self._action_size = u_dim

        self._J = jacobian_vector(f, self._inputs)
        self._Q = hessian_vector(f, self._inputs)

        self._f = as_function(f, self._inputs)

        self._f_x = as_function(self._J[:, :x_dim], self._inputs)
        self._f_u = as_function(self._J[:, x_dim:], self._inputs)

        self._has_hessians = hessians
        if hessians:
            self._f_xx = as_function(self._Q[:, :x_dim, :x_dim], self._inputs)
            self._f_ux = as_function(self._Q[:, x_dim:, :x_dim], self._inputs)
            self._f_uu = as_function(self._Q[:, x_dim:, x_dim:], self._inputs)

        super(AutoDiffDynamics, self).__init__()

    @property
    def state_size(self):
        """State size."""
        return self._state_size

    @property
    def action_size(self):
        """Action size."""
        return self._action_size

    @property
    def has_hessians(self):
        """Whether the second order derivatives are available."""
        return self._has_hessians

    @property
    def x(self):
        """The state variables."""
        return self._x_inputs

    @property
    def u(self):
        """The control variables."""
        return self._u_inputs

    def f(self, x, u):
        """Dynamics model.

        Args:
            x: Current state [state_size].
            u: Current control [control_size].

        Returns:
            Next state [state_size].
        """
        z = np.hstack([x, u])
        return self._f(*z)

    def f_x(self, x, u):
        """Partial derivative of dynamics model with respect to x.

        Args:
            x: Current state [state_size].
            u: Current control [control_size].

        Returns:
            df/dx [state_size, state_size].
        """
        z = np.hstack([x, u])
        return self._f_x(*z)

    def f_u(self, x, u):
        """Partial derivative of dynamics model with respect to u.

        Args:
            x: Current state [state_size].
            u: Current control [control_size].

        Returns:
            df/du [state_size, action_size].
        """
        z = np.hstack([x, u])
        return self._f_u(*z)

    def f_xx(self, x, u):
        """Second partial derivative of dynamics model with respect to x.

        Args:
            x: Current state [state_size].
            u: Current control [control_size].

        Returns:
            d^2f/dx^2 [state_size, state_size, state_size].
        """
        if not self._has_hessians:
            raise NotImplementedError

        z = np.hstack([x, u])
        return self._f_xx(*z)

    def f_ux(self, x, u):
        """Second partial derivative of dynamics model with respect to u and x.

        Args:
            x: Current state [state_size].
            u: Current control [control_size].

        Returns:
            d^2f/dudx [state_size, action_size, state_size].
        """
        if not self._has_hessians:
            raise NotImplementedError

        z = np.hstack([x, u])
        return self._f_ux(*z)

    def f_uu(self, x, u):
        """Second partial derivative of dynamics model with respect to u.

        Args:
            x: Current state [state_size].
            u: Current control [control_size].

        Returns:
            d^2f/du^2 [state_size, action_size, action_size].
        """
        if not self._has_hessians:
            raise NotImplementedError

        z = np.hstack([x, u])
        return self._f_uu(*z)


def constrain(u, min_bounds, max_bounds):
    """Constrains a control vector between given bounds through a squashing
    function.

    Args:
        u: Control vector [action_size].
        min_bounds: Minimum control bounds [action_size].
        max_bounds: Maximum control bounds [action_size].

    Returns:
        Constrained control vector [action_size].
    """
    diff = (max_bounds - min_bounds) / 2.0
    mean = (max_bounds + min_bounds) / 2.0
    return diff * np.tanh(u) + mean


def tensor_constrain(u, min_bounds, max_bounds):
    """Constrains a control vector tensor variable between given bounds through
    a squashing function.

    This is implemented with Theano, so as to be auto-differentiable.

    Args:
        u: Control vector tensor variable [action_size].
        min_bounds: Minimum control bounds [action_size].
        max_bounds: Maximum control bounds [action_size].

    Returns:
        Constrained control vector tensor variable [action_size].
    """
    diff = (max_bounds - min_bounds) / 2.0
    mean = (max_bounds + min_bounds) / 2.0
    return diff * T.tanh(u) + mean